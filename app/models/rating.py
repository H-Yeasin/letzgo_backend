import uuid
from sqlalchemy import Column, String, Float, Integer, ForeignKey
from sqlalchemy.types import Uuid
from app.db.base import Base, TimestampMixin


class Rating(Base, TimestampMixin):
    __tablename__ = "ratings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(Uuid(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True)
    reviewer_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    reviewed_user_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    tags = Column(String(200), nullable=True)  # comma-separated tags
    comment = Column(String(500), nullable=True)