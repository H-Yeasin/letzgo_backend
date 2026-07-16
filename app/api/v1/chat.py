from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.chat_service import ChatService
from app.schemas.chat import ChatMessageResponse
import uuid

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/{thread_id}/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
    thread_id: uuid.UUID,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Retrieve chat history for a match or match request."""
    service = ChatService(db)
    return service.get_chat_history(thread_id, uuid.UUID(user_id), limit)


from app.schemas.chat import ChatMessageCreate

@router.post("/{thread_id}", response_model=ChatMessageResponse)
async def send_chat_message(
    thread_id: uuid.UUID,
    message_in: ChatMessageCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Send a new chat message for a match or match request."""
    service = ChatService(db)
    return service.save_message(thread_id, uuid.UUID(user_id), message_in.content)
