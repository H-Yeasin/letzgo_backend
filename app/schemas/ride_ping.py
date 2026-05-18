from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class RidePingCreate(BaseModel):
    pickup_lat: float = Field(..., ge=-90, le=90)
    pickup_lng: float = Field(..., ge=-180, le=180)
    pickup_area: Optional[str] = None
    destination_text: str = Field(..., min_length=3, max_length=300)
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    estimated_fare: float = Field(..., gt=0)
    gender_preference: str = Field(default="any", pattern=r"^(any|male|female)$")
    meetup_point: Optional[str] = None
    passenger_limit: int = Field(default=1, ge=1, le=5)
    expires_in_minutes: int = Field(default=30, ge=5, le=120)


class RidePingUpdate(BaseModel):
    estimated_fare: Optional[float] = None
    final_fare: Optional[float] = None
    gender_preference: Optional[str] = None
    meetup_point: Optional[str] = None
    status: Optional[str] = None


class RidePingResponse(BaseModel):
    id: UUID
    host_id: UUID
    pickup_lat: float
    pickup_lng: float
    pickup_area: Optional[str] = None
    destination_text: str
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    estimated_fare: float
    final_fare: Optional[float] = None
    gender_preference: str
    meetup_point: Optional[str] = None
    passenger_limit: int
    status: str
    expires_at: datetime
    created_at: datetime
    host: Optional["UserPublicProfile"] = None

    class Config:
        from_attributes = True


class RidePingListParams(BaseModel):
    """Query parameters for searching nearby ride pings."""
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(default=500, ge=100, le=5000)
    gender_preference: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=50)


# Import for forward reference
from app.schemas.user import UserPublicProfile
RidePingResponse.model_rebuild()