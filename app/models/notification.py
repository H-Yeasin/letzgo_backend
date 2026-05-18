import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Text
from sqlalchemy.types import Uuid
from app.db.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(Text, nullable=True)  # JSON string
    type = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False)