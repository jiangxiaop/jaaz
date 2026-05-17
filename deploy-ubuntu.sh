#!/usr/bin/env bash
#
# Jaaz Backend - Ubuntu Server Deployment Script
# Usage: bash deploy-ubuntu.sh
#
set -e

# ============== Configuration ==============
APP_NAME="jaaz"
APP_USER="jaaz"
INSTALL_DIR="/opt/jaaz"
REPO_URL="https://github.com/jiangxiaop/jaaz.git"
PYTHON_VERSION="3.12"
NODE_VERSION="20"
SERVER_PORT=57988
BUILD_FRONTEND="no"              # "yes" to build and serve frontend from backend

# API Keys (leave empty to skip)
OPENAI_API_KEY=""                 # OpenAI direct: sk-xxxxx
JAAZ_API_KEY=""                   # Jaaz platform token
OLLAMA_URL=""
COMFYUI_URL=""
MAX_TOKENS=8192

# Custom providers: add as many as needed
# Format: "name|url|api_key|model1:type,model2:type"
# Example: "azure|https://myazure.openai.azure.com/v1/|sk-xxx|gpt-4o:text,gpt-4o-mini:text"
CUSTOM_PROVIDERS=(
  # "deepseek|https://api.deepseek.com/v1/|sk-xxx|deepseek-chat:text"
  "openrouter|https://airoutingapi.jyczg888.uk/|sk-053d7fedc57a57045a85ccb207609fab435c1cc568b0344a4122535b1cc4e588|openai/gpt-4o:text,anthropic/claude-sonnet-4:text"
)

# Nginx
NGINX_LISTEN_PORT=80
NGINX_SERVER_NAME="aiapi.funblocks.app"             # "_" matches any domain, or set "your-domain.com"
CLIENT_MAX_BODY_SIZE="200M"
PROXY_TIMEOUT="300s"
REMOVE_DEFAULT_SITE="yes"         # "yes" to remove /etc/nginx/sites-enabled/default
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------- 0. Root check ----------
if [ "$EUID" -ne 0 ]; then
  err "Please run as root: sudo bash deploy-ubuntu.sh"
fi

# ---------- 1. System dependencies ----------
log "Installing system dependencies..."
apt-get update -y
apt-get install -y \
  software-properties-common \
  git curl wget \
  build-essential \
  libmediainfo-dev \
  nginx

# ---------- 2. Install Python >= 3.12 ----------
# Try exact version first (e.g. python3.12), then fall back to system python3
PYTHON_CMD=""
if command -v "python${PYTHON_VERSION}" &>/dev/null; then
  PYTHON_CMD="python${PYTHON_VERSION}"
elif command -v python3 &>/dev/null; then
  SYS_PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  SYS_PY_MAJOR=$(echo "$SYS_PY_VER" | cut -d. -f1)
  SYS_PY_MINOR=$(echo "$SYS_PY_VER" | cut -d. -f2)
  if [ "$SYS_PY_MAJOR" -ge 3 ] && [ "$SYS_PY_MINOR" -ge 12 ]; then
    PYTHON_CMD="python3"
    log "Using system Python: $SYS_PY_VER"
  fi
fi

if [ -z "$PYTHON_CMD" ]; then
  log "No Python >= 3.12 found, attempting to install via deadsnakes PPA..."
  add-apt-repository -y ppa:deadsnakes/ppa
  apt-get update -y
  apt-get install -y "python${PYTHON_VERSION}" "python${PYTHON_VERSION}-venv" "python${PYTHON_VERSION}-dev"
  PYTHON_CMD="python${PYTHON_VERSION}"
fi

# Ensure venv module is available
apt-get install -y python3-venv python3-dev 2>/dev/null || true

log "Python command: ${PYTHON_CMD} ($(${PYTHON_CMD} --version))"

# ---------- 3. Install Node.js (for frontend build) ----------
if [ "$BUILD_FRONTEND" = "yes" ]; then
  if ! command -v node &>/dev/null || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt "$NODE_VERSION" ]; then
    log "Installing Node.js ${NODE_VERSION}..."
    curl -fsSL "https://deb.nodesource.com/setup_${NODE_VERSION}.x" | bash -
    apt-get install -y nodejs
  else
    log "Node.js already installed: $(node -v)"
  fi
fi

# ---------- 4. Create app user ----------
if ! id "$APP_USER" &>/dev/null; then
  log "Creating user: ${APP_USER}"
  useradd -r -m -s /bin/bash "$APP_USER"
fi

# ---------- 5. Clone / update source code ----------
if [ -d "${INSTALL_DIR}/.git" ]; then
  log "Updating existing repo..."
  cd "$INSTALL_DIR"
  sudo -u "$APP_USER" git pull --ff-only || warn "Git pull failed, using existing code."
else
  log "Cloning repo to ${INSTALL_DIR}..."
  git clone "$REPO_URL" "$INSTALL_DIR"
  chown -R "$APP_USER":"$APP_USER" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ---------- 6. Python venv & dependencies ----------
log "Setting up Python virtual environment..."
sudo -u "$APP_USER" "$PYTHON_CMD" -m venv "${INSTALL_DIR}/venv"
VENV_PIP="${INSTALL_DIR}/venv/bin/pip"
VENV_PYTHON="${INSTALL_DIR}/venv/bin/python"

sudo -u "$APP_USER" "$VENV_PIP" install --upgrade pip
sudo -u "$APP_USER" "$VENV_PIP" install -r "${INSTALL_DIR}/server/requirements.txt"

# ---------- 7. Build frontend (optional) ----------
if [ "$BUILD_FRONTEND" = "yes" ]; then
  log "Building React frontend..."
  cd "${INSTALL_DIR}/react"
  sudo -u "$APP_USER" npm install --force
  sudo -u "$APP_USER" npx vite build
  cd "$INSTALL_DIR"
fi

# ---------- 8. Generate config.toml ----------
USER_DATA_DIR="${INSTALL_DIR}/server/user_data"
CONFIG_FILE="${USER_DATA_DIR}/config.toml"

sudo -u "$APP_USER" mkdir -p "$USER_DATA_DIR"

if [ -f "$CONFIG_FILE" ]; then
  log "config.toml already exists, skipping generation (delete it to regenerate)."
else
  log "Generating config.toml..."
  cat > "$CONFIG_FILE" <<TOML
[jaaz]
url = "https://jaaz.app/api/v1/"
api_key = "${JAAZ_API_KEY}"
max_tokens = ${MAX_TOKENS}

[jaaz.models."gpt-4o"]
type = "text"

[jaaz.models."gpt-4o-mini"]
type = "text"

[jaaz.models."deepseek/deepseek-chat-v3-0324"]
type = "text"

[jaaz.models."anthropic/claude-sonnet-4"]
type = "text"

[jaaz.models."anthropic/claude-3.7-sonnet"]
type = "text"

[openai]
url = "https://api.openai.com/v1/"
api_key = "${OPENAI_API_KEY}"
max_tokens = ${MAX_TOKENS}

[openai.models."gpt-4o"]
type = "text"

[openai.models."gpt-4o-mini"]
type = "text"

[ollama]
url = "${OLLAMA_URL}"
api_key = ""
max_tokens = ${MAX_TOKENS}

[ollama.models]

[comfyui]
url = "${COMFYUI_URL}"
api_key = ""

[comfyui.models]
TOML

  # Append custom providers
  for entry in "${CUSTOM_PROVIDERS[@]}"; do
    IFS='|' read -r pname purl pkey pmodels <<< "$entry"
    [ -z "$pname" ] && continue
    cat >> "$CONFIG_FILE" <<TOML

[${pname}]
url = "${purl}"
api_key = "${pkey}"
max_tokens = ${MAX_TOKENS}
is_custom = true
TOML
    # Parse models: "model1:type,model2:type"
    IFS=',' read -ra model_list <<< "$pmodels"
    for m in "${model_list[@]}"; do
      IFS=':' read -r mname mtype <<< "$m"
      mtype="${mtype:-text}"
      cat >> "$CONFIG_FILE" <<TOML

[${pname}.models."${mname}"]
type = "${mtype}"
is_custom = true
TOML
    done
  done

  chown "$APP_USER":"$APP_USER" "$CONFIG_FILE"
  log "config.toml created at ${CONFIG_FILE}"
fi

# ---------- 9. Create systemd service ----------
log "Creating systemd service..."
cat > "/etc/systemd/system/${APP_NAME}.service" <<EOF
[Unit]
Description=Jaaz Backend Server
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${INSTALL_DIR}/server
Environment="PATH=${INSTALL_DIR}/venv/bin:/usr/bin:/bin"
Environment="HOME=/home/${APP_USER}"
ExecStart=${VENV_PYTHON} main.py --port ${SERVER_PORT}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ---------- 10. Configure Nginx reverse proxy ----------
log "Configuring Nginx..."
cat > "/etc/nginx/sites-available/${APP_NAME}" <<NGINX
server {
    listen ${NGINX_LISTEN_PORT};
    server_name ${NGINX_SERVER_NAME};

    client_max_body_size ${CLIENT_MAX_BODY_SIZE};
    proxy_read_timeout ${PROXY_TIMEOUT};
    proxy_send_timeout ${PROXY_TIMEOUT};

    # WebSocket (Socket.IO)
    location /socket.io/ {
        proxy_pass http://127.0.0.1:${SERVER_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # All other requests
    location / {
        proxy_pass http://127.0.0.1:${SERVER_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

ln -sf "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-enabled/${APP_NAME}"
if [ "$REMOVE_DEFAULT_SITE" = "yes" ]; then
  rm -f /etc/nginx/sites-enabled/default
fi
nginx -t && systemctl reload nginx

# ---------- 11. Start service ----------
log "Starting ${APP_NAME} service..."
systemctl daemon-reload
systemctl enable "${APP_NAME}"
systemctl restart "${APP_NAME}"

# ---------- 12. Summary ----------
echo ""
echo "=========================================="
log "Jaaz backend deployed successfully!"
echo ""
echo "  Install dir : ${INSTALL_DIR}"
echo "  Config file : ${CONFIG_FILE}"
echo "  Backend port: ${SERVER_PORT}"
echo "  Service     : systemctl status ${APP_NAME}"
echo "  Logs        : journalctl -u ${APP_NAME} -f"
echo "  Nginx       : http://<your-server-ip>:${NGINX_LISTEN_PORT}"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl restart ${APP_NAME}   # restart"
echo "    sudo systemctl stop ${APP_NAME}      # stop"
echo "    sudo journalctl -u ${APP_NAME} -f    # live logs"
echo "=========================================="
