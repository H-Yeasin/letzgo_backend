import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.types import Uuid
from app.db.base import Base, TimestampMixin


class DeviceToken(Base, TimestampMixin):
    __tablename__ = "device_tokens"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    token = Column(String(255), nullable=False, index=True)
    platform = Column(String(20), nullable=True)  # ios, android, web
