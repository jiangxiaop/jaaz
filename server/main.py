import os
import sys
import io
# Ensure stdout and stderr use utf-8 encoding to prevent emoji logs from crashing python server
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
print('Importing websocket_router')
from routers.websocket_router import *  # DO NOT DELETE THIS LINE, OTHERWISE, WEBSOCKET WILL NOT WORK
print('Importing routers')
from routers import config_router, image_router, root_router, workspace, canvas, ssl_test, chat_router, settings, tool_confirmation, auth_router
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
import argparse
from contextlib import asynccontextmanager
from starlette.types import Scope
from starlette.responses import Response
import socketio # type: ignore
print('Importing websocket_state')
from services.websocket_state import sio
print('Importing websocket_service')
from services.websocket_service import broadcast_init_done
print('Importing config_service')
from services.config_service import config_service
print('Importing tool_service')
from services.tool_service import tool_service

async def initialize():
    print('Initializing config_service')
    await config_service.initialize()
    print('Initializing broadcast_init_done')
    await broadcast_init_done()

root_dir = os.path.dirname(__file__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # onstartup
    # TODO: Check if there will be racing conditions when user send chat request but tools and models are not initialized yet.
    await initialize()
    await tool_service.initialize()
    yield
    # onshutdown

print('Creating FastAPI app')
app = FastAPI(lifespan=lifespan)

# CORS
from fastapi.middleware.cors import CORSMiddleware
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS.split(",") if CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
print('Including routers')
app.include_router(config_router.router)
app.include_router(settings.router)
app.include_router(root_router.router)
app.include_router(canvas.router)
app.include_router(workspace.router)
app.include_router(image_router.router)
app.include_router(ssl_test.router)
app.include_router(chat_router.router)
app.include_router(tool_confirmation.router)
app.include_router(auth_router.router)

# Mount the React build directory
react_build_dir = os.environ.get('UI_DIST_DIR', os.path.join(
    os.path.dirname(root_dir), "react", "dist"))


# 无缓存静态文件类
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


static_site = os.path.join(react_build_dir, "assets")
if os.path.exists(static_site):
    app.mount("/assets", NoCacheStaticFiles(directory=static_site), name="assets")


@app.get("/")
async def serve_react_app():
    response = FileResponse(os.path.join(react_build_dir, "index.html"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

print('Creating socketio app')
_socket_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path='/socket.io')

# Wrap socket_app with CORS headers so /api/file/ and other non-socketio
# routes get proper CORS even when going through the socketio ASGI layer.
class CORSWrapperASGI:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers_to_add = [
                (b"access-control-allow-origin", CORS_ORIGINS.encode() if CORS_ORIGINS != "*" else b"*"),
                (b"access-control-allow-credentials", b"true"),
                (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                (b"access-control-allow-headers", b"Content-Type, Authorization"),
            ]
            # Handle preflight
            if scope.get("method") == "OPTIONS":
                await send({"type": "http.response.start", "status": 204, "headers": headers_to_add})
                await send({"type": "http.response.body", "body": b""})
                return

            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    existing = dict(message.get("headers", []))
                    # Only add if not already set by FastAPI CORS middleware
                    if b"access-control-allow-origin" not in existing:
                        message["headers"] = list(message.get("headers", [])) + headers_to_add
                await send(message)
            await self.app(scope, receive, send_with_cors)
        else:
            await self.app(scope, receive, send)

socket_app = CORSWrapperASGI(_socket_app)

if __name__ == "__main__":
    # bypass localhost request for proxy, fix ollama proxy issue
    _bypass = {"127.0.0.1", "localhost", "::1"}
    current = set(os.environ.get("no_proxy", "").split(",")) | set(
        os.environ.get("NO_PROXY", "").split(","))
    os.environ["no_proxy"] = os.environ["NO_PROXY"] = ",".join(
        sorted(_bypass | current - {""}))

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=57988,
                        help='Port to run the server on')
    args = parser.parse_args()
    import uvicorn
    print("🌟Starting server, UI_DIST_DIR:", os.environ.get('UI_DIST_DIR'))

    uvicorn.run(socket_app, host="127.0.0.1", port=args.port)
