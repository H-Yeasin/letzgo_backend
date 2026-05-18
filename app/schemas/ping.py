from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.schemas.user import UserPublicProfile


class RidePingBase(BaseModel):
    pickup_label: str
    destination_label: str
    estimated_fare: float
    gender_preference: str = "any"  # any, male_only, female_only
    max_passengers: int = 1
    meetup_point: Optional[str] = None


class RidePingCreate(RidePingBase):
    pickup_lat: float
    pickup_lng: float
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    expires_in_minutes: int = 30


class RidePingUpdate(BaseModel):
    pickup_label: Optional[str] = None
    destination_label: Optional[str] = None
    estimated_fare: Optional[float] = None
    final_fare: Optional[float] = None
    gender_preference: Optional[str] = None
    meetup_point: Optional[str] = None
    status: Optional[str] = None


class NearbyHostProfile(BaseModel):
    """Limited host profile visible in the nearby feed before joining."""
    id: UUID
    gender: Optional[str] = None
    rating: float = 0.0
    trust_level: str = "unknown"  # low, medium, high

    class Config:
        from_attributes = True


class RidePingNearbyResponse(BaseModel):
    """Response shape for the nearby feed (GET /pings/nearby)."""
    ride_id: UUID
    host: NearbyHostProfile
    pickup_label: Optional[str] = None
    destination_label: str
    estimated_fare: float
    available_seats: int
    gender_preference: str
    distance_meters: float

    class Config:
        from_attributes = True


class RidePingResponse(BaseModel):
    id: UUID
    host_id: UUID
    pickup_lat: float
    pickup_lng: float
    pickup_label: Optional[str] = None
    destination_label: str
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    estimated_fare: float
    final_fare: Optional[float] = None
    gender_preference: str
    meetup_point: Optional[str] = None
    max_passengers: int
    current_passengers: int = 0
    status: str
    expires_at: datetime
    created_at: datetime
    host: Optional[UserPublicProfile] = None

    class Config:
        from_attributes = True


class RidePingListResponse(BaseModel):
    total: int
    items: List[RidePingResponse]


class RidePingNearbyListResponse(BaseModel):
    total: int
    items: List[RidePingNearbyResponse]


class DeleteExpiredPingsResponse(BaseModel):
    deleted: int
