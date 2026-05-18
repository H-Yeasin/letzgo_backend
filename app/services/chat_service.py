import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models.chat_message import ChatMessage
from app.models.match import Match
from app.core.exceptions import ForbiddenException, NotFoundException


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def save_message(self, match_id: uuid.UUID, sender_id: uuid.UUID, content: str) -> ChatMessage:
        """Save a new chat message."""
        # Verify user is part of the match
        match = self.db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise NotFoundException(detail="Match not found")
        
        if match.host_id != sender_id and match.guest_id != sender_id:
            raise ForbiddenException(detail="Not authorized to chat in this match")

        message = ChatMessage(
            match_id=match_id,
            sender_id=sender_id,
            content=content
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_chat_history(self, match_id: uuid.UUID, user_id: uuid.UUID, limit: int = 100) -> List[ChatMessage]:
        """Get history for a match."""
        # Verify user is part of the match
        match = self.db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise NotFoundException(detail="Match not found")
        
        if match.host_id != user_id and match.guest_id != user_id:
            raise ForbiddenException(detail="Not authorized to view this chat")

        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.match_id == match_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()[::-1] # Ascending order for UI
        )