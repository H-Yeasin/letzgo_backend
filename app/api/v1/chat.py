from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.chat_service import ChatService
from app.schemas.chat import ChatMessageResponse
import uuid

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/{match_id}/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
    match_id: uuid.UUID,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Retrieve chat history for a match."""
    service = ChatService(db)
    return service.get_chat_history(match_id, uuid.UUID(user_id), limit)
