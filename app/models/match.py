import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class Match(Base, TimestampMixin):
    __tablename__ = "matches"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ride_id = Column(Uuid(as_uuid=True), ForeignKey("ride_pings.id"), nullable=False, index=True)
    host_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    guest_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    status = Column(String(20), default="matched")  # matched, in_progress, completed, cancelled, disputed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    ride = relationship("RidePing", foreign_keys=[ride_id], lazy="joined")
    host = relationship("User", foreign_keys=[host_id], lazy="joined")
    guest = relationship("User", foreign_keys=[guest_id], lazy="joined")