from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.schemas.ping import RidePingResponse
from app.schemas.user import UserPublicProfile


class MatchRequestCreate(BaseModel):
    ride_id: UUID


class MatchRequestUserInfo(BaseModel):
    """User info visible to host on a join request."""
    id: UUID
    name: str
    gender: Optional[str] = None
    rating_avg: float = 0.0

    class Config:
        from_attributes = True


class MatchRequestResponse(BaseModel):
    id: UUID
    ride_id: UUID
    guest_id: UUID
    host_id: UUID
    status: str  # pending, accepted, declined, cancelled
    created_at: datetime

    class Config:
        from_attributes = True


class MatchRequestWithUserResponse(BaseModel):
    """Match request with guest user info, for host to see who requested."""
    id: UUID
    ride_id: UUID
    guest: MatchRequestUserInfo
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class MatchResponse(BaseModel):
    id: UUID
    ride_id: UUID
    host_id: UUID
    guest_id: UUID
    status: str  # matched, in_progress, completed, cancelled
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    host: Optional[UserPublicProfile] = None
    guest: Optional[UserPublicProfile] = None
    ride: Optional[RidePingResponse] = None

    class Config:
        from_attributes = True


class MatchDetailResponse(MatchResponse):
    class Config:
        from_attributes = True


class MatchCompleteRequest(BaseModel):
    final_fare: float