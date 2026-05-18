import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class MatchRequest(Base, TimestampMixin):
    __tablename__ = "match_requests"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ride_id = Column(Uuid(as_uuid=True), ForeignKey("ride_pings.id"), nullable=False, index=True)
    guest_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    host_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    status = Column(String(20), default="pending")  # pending, accepted, declined, cancelled

    # Relationships
    guest = relationship("User", foreign_keys=[guest_id], lazy="joined")
    host = relationship("User", foreign_keys=[host_id], lazy="joined")
    ride = relationship("RidePing", foreign_keys=[ride_id], lazy="joined")