from fastapi import APIRouter, Request
from services.chat_service import handle_chat
from services.db_service import db_service
from services.auth_service import get_user_id_from_request
import asyncio
import json

router = APIRouter(prefix="/api/canvas")

@router.get("/list")
async def list_canvases(request: Request):
    user_id = get_user_id_from_request(request)
    return await db_service.list_canvases(user_id)

@router.post("/create")
async def create_canvas(request: Request):
    user_id = get_user_id_from_request(request)
    data = await request.json()
    id = data.get('canvas_id')
    name = data.get('name')

    asyncio.create_task(handle_chat(data, user_id))
    await db_service.create_canvas(id, name, user_id)
    return {"id": id }

@router.get("/{id}")
async def get_canvas(id: str, request: Request):
    user_id = get_user_id_from_request(request)
    return await db_service.get_canvas_data(id, user_id)

@router.post("/{id}/save")
async def save_canvas(id: str, request: Request):
    payload = await request.json()
    data_str = json.dumps(payload['data'])
    await db_service.save_canvas_data(id, data_str, payload['thumbnail'])
    return {"id": id }

@router.post("/{id}/rename")
async def rename_canvas(id: str, request: Request):
    user_id = get_user_id_from_request(request)
    data = await request.json()
    name = data.get('name')
    await db_service.rename_canvas(id, name, user_id)
    return {"id": id }

@router.delete("/{id}/delete")
async def delete_canvas(id: str, request: Request):
    user_id = get_user_id_from_request(request)
    await db_service.delete_canvas(id, user_id)
    return {"id": id }
