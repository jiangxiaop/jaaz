#server/routers/chat_router.py
from fastapi import APIRouter, Request
from services.chat_service import handle_chat
from services.stream_service import get_stream_task

router = APIRouter(prefix="/api")

@router.post("/chat")
async def chat(request: Request):
    data = await request.json()
    await handle_chat(data)
    return {"status": "done"}

@router.post("/cancel/{session_id}")
async def cancel_chat(session_id: str):
    task = get_stream_task(session_id)
    if task and not task.done():
        task.cancel()
        return {"status": "cancelled"}
    return {"status": "not_found_or_done"}
