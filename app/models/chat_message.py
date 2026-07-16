import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.types import Uuid
from app.db.base import Base, TimestampMixin


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(Uuid(as_uuid=True), ForeignKey("matches.id"), nullable=True, index=True)
    request_id = Column(Uuid(as_uuid=True), ForeignKey("match_requests.id"), nullable=True, index=True)
    sender_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    message = Column(String(500), nullable=False)