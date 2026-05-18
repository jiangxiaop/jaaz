#server/routers/chat_router.py
from fastapi import APIRouter, Request, HTTPException
from services.chat_service import handle_chat
from services.stream_service import get_stream_task
from services.auth_service import get_user_id_from_request

router = APIRouter(prefix="/api")

@router.post("/chat")
async def chat(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = await request.json()
    await handle_chat(data, user_id)
    return {"status": "done"}

@router.post("/cancel/{session_id}")
async def cancel_chat(session_id: str):
    task = get_stream_task(session_id)
    if task and not task.done():
        task.cancel()
        return {"status": "cancelled"}
    return {"status": "not_found_or_done"}
