#!/usr/bin/env bash
#
# Jaaz Backend - Pull & Redeploy Script
# Usage: sudo bash update-ubuntu.sh
#
set -e

# ============== Configuration ==============
APP_NAME="jaaz"
APP_USER="jaaz"
INSTALL_DIR="/opt/jaaz"
GIT_BRANCH="main"
SERVER_PORT=57988
BUILD_FRONTEND="no"              # "yes" to rebuild frontend after pull
UPDATE_DEPS="auto"               # "auto" = only if requirements.txt changed, "yes" = always, "no" = skip
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------- 0. Checks ----------
if [ "$EUID" -ne 0 ]; then
  err "Please run as root: sudo bash update-ubuntu.sh"
fi

if [ ! -d "${INSTALL_DIR}/.git" ]; then
  err "${INSTALL_DIR} is not a git repo. Run deploy-ubuntu.sh first."
fi

VENV_PIP="${INSTALL_DIR}/venv/bin/pip"
VENV_PYTHON="${INSTALL_DIR}/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
  err "Python venv not found at ${INSTALL_DIR}/venv. Run deploy-ubuntu.sh first."
fi

cd "$INSTALL_DIR"

# ---------- 1. Record old state ----------
OLD_REQ_HASH=$(md5sum server/requirements.txt 2>/dev/null | cut -d' ' -f1 || echo "none")
OLD_COMMIT=$(sudo -u "$APP_USER" git rev-parse HEAD)

# ---------- 2. Pull latest code ----------
log "Pulling latest code from ${GIT_BRANCH}..."
sudo -u "$APP_USER" git fetch origin "$GIT_BRANCH"
sudo -u "$APP_USER" git reset --hard "origin/${GIT_BRANCH}"
NEW_COMMIT=$(sudo -u "$APP_USER" git rev-parse HEAD)

if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
  log "Already up to date (${NEW_COMMIT:0:8}). No restart needed."
  exit 0
fi

# Show changes
log "Updated: ${OLD_COMMIT:0:8} -> ${NEW_COMMIT:0:8}"
echo ""
sudo -u "$APP_USER" git log --oneline "${OLD_COMMIT}..${NEW_COMMIT}"
echo ""

# ---------- 3. Update Python dependencies ----------
NEW_REQ_HASH=$(md5sum server/requirements.txt 2>/dev/null | cut -d' ' -f1 || echo "none")

if [ "$UPDATE_DEPS" = "yes" ] || { [ "$UPDATE_DEPS" = "auto" ] && [ "$OLD_REQ_HASH" != "$NEW_REQ_HASH" ]; }; then
  log "Updating Python dependencies..."
  sudo -u "$APP_USER" "$VENV_PIP" install --upgrade pip
  sudo -u "$APP_USER" "$VENV_PIP" install -r "${INSTALL_DIR}/server/requirements.txt"
else
  log "Python dependencies unchanged, skipping."
fi

# ---------- 4. Rebuild frontend (optional) ----------
if [ "$BUILD_FRONTEND" = "yes" ]; then
  log "Rebuilding React frontend..."
  cd "${INSTALL_DIR}/react"
  sudo -u "$APP_USER" npm install --force
  sudo -u "$APP_USER" npx vite build
  cd "$INSTALL_DIR"
fi

# ---------- 5. Restart service ----------
log "Restarting ${APP_NAME} service..."
systemctl restart "$APP_NAME"

# Wait a moment and check status
sleep 2
if systemctl is-active --quiet "$APP_NAME"; then
  log "Service restarted successfully."
else
  err "Service failed to start! Check logs: journalctl -u ${APP_NAME} -n 50"
fi

# ---------- 6. Verify ----------
sleep 1
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${SERVER_PORT}/api/config" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
  log "Health check passed (HTTP ${HTTP_CODE})."
else
  warn "Health check returned HTTP ${HTTP_CODE}. Check logs: journalctl -u ${APP_NAME} -f"
fi

# ---------- 7. Summary ----------
echo ""
echo "=========================================="
log "Update complete!"
echo ""
echo "  Commit : ${NEW_COMMIT:0:8}"
echo "  Deps   : $([ "$OLD_REQ_HASH" != "$NEW_REQ_HASH" ] && echo 'updated' || echo 'unchanged')"
echo "  Service: $(systemctl is-active $APP_NAME)"
echo "  API    : HTTP ${HTTP_CODE}"
echo ""
echo "  View logs: sudo journalctl -u ${APP_NAME} -f"
echo "=========================================="
