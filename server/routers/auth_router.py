from fastapi import APIRouter, Request
from services.auth_service import register_user, login_user, get_user_by_token

router = APIRouter(prefix="/api/auth")


@router.post("/register")
async def register(request: Request):
    data = await request.json()
    return await register_user(data.get("username", ""), data.get("password", ""))


@router.post("/login")
async def login(request: Request):
    data = await request.json()
    return await login_user(data.get("username", ""), data.get("password", ""))


@router.get("/me")
async def me(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"status": "error", "message": "Not authenticated"}

    token = auth_header[7:]
    user_info = await get_user_by_token(token)
    if not user_info:
        return {"status": "error", "message": "Token expired or invalid"}

    return {"status": "success", "user_info": user_info}
