import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.types import Uuid
from app.db.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    reported_user_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    match_id = Column(Uuid(as_uuid=True), ForeignKey("matches.id"), nullable=True)
    reason = Column(String(50), nullable=False)  # harassment, no_show, payment_issue, fake_profile, unsafe_behavior
    description = Column(String(500), nullable=True)
    status = Column(String(20), default="pending")  # pending, reviewed, resolved, dismissed