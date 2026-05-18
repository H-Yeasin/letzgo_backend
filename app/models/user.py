import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.types import Uuid
from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "profiles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    gender = Column(String(10), nullable=True)  # male, female, other
    avatar_url = Column(String(500), nullable=True)
    rating_avg = Column(Float, default=0.0)
    completed_rides_count = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    is_onboarding_complete = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    fcm_token = Column(String(500), nullable=True)
    device_token = Column(String(500), nullable=True)