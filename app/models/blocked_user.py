import uuid
from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import Uuid
from app.db.base import Base, TimestampMixin


class BlockedUser(Base, TimestampMixin):
    __tablename__ = "blocked_users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    blocked_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)