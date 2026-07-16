import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.base import Base, TimestampMixin
from app.utils.geo import extract_coordinates


class RidePing(Base, TimestampMixin):
    __tablename__ = "ride_pings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    pickup_geom = Column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    pickup_label = Column(String(200), nullable=True)
    destination_label = Column(String(300), nullable=False)
    destination_geom = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    estimated_fare = Column(Float, nullable=False)
    final_fare = Column(Float, nullable=True)
    gender_preference = Column(String(10), default="any")  # any, male_only, female_only
    meetup_point = Column(String(200), nullable=True)
    max_passengers = Column(Integer, default=1)
    current_passengers = Column(Integer, default=0)
    status = Column(String(20), default="open")  # open, matched, in_progress, completed, cancelled, expired
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    host = relationship("User", foreign_keys=[host_id], lazy="joined")

    # Coordinate accessors so pydantic schemas (from_attributes) can serialize
    # the PostGIS geometry columns as plain lat/lng floats.
    @property
    def pickup_lat(self):
        return extract_coordinates(self.pickup_geom)[0]

    @property
    def pickup_lng(self):
        return extract_coordinates(self.pickup_geom)[1]

    @property
    def destination_lat(self):
        return extract_coordinates(self.destination_geom)[0]

    @property
    def destination_lng(self):
        return extract_coordinates(self.destination_geom)[1]