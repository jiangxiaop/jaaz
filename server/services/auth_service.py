import os
import sqlite3
from typing import Optional, Dict, Any
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
import aiosqlite
from nanoid import generate as nanoid
from .config_service import USER_DATA_DIR

DB_PATH = os.path.join(USER_DATA_DIR, "localmanus.db")

JWT_SECRET = os.getenv("JWT_SECRET", "funblocks-default-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def register_user(username: str, password: str) -> Dict[str, Any]:
    if not username or not password:
        return {"status": "error", "message": "Username and password are required"}

    if len(username) < 2 or len(username) > 32:
        return {"status": "error", "message": "Username must be 2-32 characters"}

    if len(password) < 6:
        return {"status": "error", "message": "Password must be at least 6 characters"}

    user_id = nanoid(size=12)
    pw_hash = hash_password(password)

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
                (user_id, username, pw_hash),
            )
            await db.commit()
    except aiosqlite.IntegrityError:
        return {"status": "error", "message": "Username already exists"}

    token = create_token(user_id, username)
    return {
        "status": "success",
        "token": token,
        "user_info": {
            "id": user_id,
            "username": username,
        },
    }


async def login_user(username: str, password: str) -> Dict[str, Any]:
    if not username or not password:
        return {"status": "error", "message": "Username and password are required"}

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cursor = await db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        )
        row = await cursor.fetchone()

    if not row:
        return {"status": "error", "message": "Invalid username or password"}

    if not verify_password(password, row["password_hash"]):
        return {"status": "error", "message": "Invalid username or password"}

    token = create_token(row["id"], row["username"])
    return {
        "status": "success",
        "token": token,
        "user_info": {
            "id": row["id"],
            "username": row["username"],
        },
    }


async def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    payload = decode_token(token)
    if not payload:
        return None

    return {
        "id": payload["sub"],
        "username": payload["username"],
    }
