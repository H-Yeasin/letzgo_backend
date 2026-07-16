import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models.chat_message import ChatMessage
from app.models.match import Match
from app.models.match_request import MatchRequest
from app.core.exceptions import ForbiddenException, NotFoundException


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def save_message(self, thread_id: uuid.UUID, sender_id: uuid.UUID, content: str) -> ChatMessage:
        """Save a new chat message for a Match or MatchRequest."""
        # Check if it's a match
        match = self.db.query(Match).filter(Match.id == thread_id).first()
        is_request = False
        if match:
            if match.host_id != sender_id and match.guest_id != sender_id:
                raise ForbiddenException(detail="Not authorized to chat in this match")
        else:
            # Check if it's a request
            request = self.db.query(MatchRequest).filter(MatchRequest.id == thread_id).first()
            if not request:
                raise NotFoundException(detail="Match or Request not found")
            if request.host_id != sender_id and request.guest_id != sender_id:
                raise ForbiddenException(detail="Not authorized to chat in this request")
            is_request = True

        message = ChatMessage(
            match_id=None if is_request else thread_id,
            request_id=thread_id if is_request else match.request_id,
            sender_id=sender_id,
            message=content
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_chat_history(self, thread_id: uuid.UUID, user_id: uuid.UUID, limit: int = 100) -> List[ChatMessage]:
        """Get history for a match or request."""
        match = self.db.query(Match).filter(Match.id == thread_id).first()
        is_request = False
        request_id_to_fetch = None

        if match:
            if match.host_id != user_id and match.guest_id != user_id:
                raise ForbiddenException(detail="Not authorized to view this chat")
            request_id_to_fetch = match.request_id
        else:
            request = self.db.query(MatchRequest).filter(MatchRequest.id == thread_id).first()
            if not request:
                raise NotFoundException(detail="Match or Request not found")
            if request.host_id != user_id and request.guest_id != user_id:
                raise ForbiddenException(detail="Not authorized to view this chat")
            is_request = True
            request_id_to_fetch = thread_id

        # Fetch messages matching either the match_id or the associated request_id
        from sqlalchemy import or_
        filters = []
        if not is_request:
            filters.append(ChatMessage.match_id == thread_id)
        if request_id_to_fetch:
            filters.append(ChatMessage.request_id == request_id_to_fetch)
        
        return (
            self.db.query(ChatMessage)
            .filter(or_(*filters))
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()[::-1] # Ascending order for UI
        )