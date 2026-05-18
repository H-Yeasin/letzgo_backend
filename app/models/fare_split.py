import uuid
from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.types import Uuid
from app.db.base import Base, TimestampMixin


class FareSplit(Base, TimestampMixin):
    __tablename__ = "fare_splits"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(Uuid(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True)
    host_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    guest_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    total_fare = Column(Float, nullable=False)
    guest_share = Column(Float, nullable=False)
    host_share = Column(Float, nullable=False)
    guest_status = Column(String(20), default="pending")  # pending, paid, confirmed, disputed
    host_status = Column(String(20), default="pending")  # pending, paid, confirmed, disputed
