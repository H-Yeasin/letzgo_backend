from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ---- Auth ----
class AdminLoginRequest(BaseModel):
    phone: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = True


# ---- User Management ----
class AdminUserResponse(BaseModel):
    id: UUID
    phone: str
    name: str
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    rating_avg: float = 0.0
    completed_rides_count: int = 0
    is_verified: bool = False
    is_blocked: bool = False
    is_admin: bool = False
    is_onboarding_complete: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    total: int
    users: List[AdminUserResponse]


# ---- Rides ----
class AdminRideResponse(BaseModel):
    id: UUID
    host_id: UUID
    host_name: Optional[str] = None
    pickup_label: Optional[str] = None
    destination_label: str
    estimated_fare: float
    final_fare: Optional[float] = None
    status: str
    gender_preference: str = "any"
    max_passengers: int = 1
    current_passengers: int = 0
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    guest_count: int = 0
    cancelled_count: int = 0

    class Config:
        from_attributes = True


class AdminRideListResponse(BaseModel):
    total: int
    rides: List[AdminRideResponse]


# ---- Reports ----
class AdminReportResponse(BaseModel):
    id: UUID
    reporter_id: UUID
    reporter_name: Optional[str] = None
    reported_user_id: UUID
    reported_user_name: Optional[str] = None
    match_id: Optional[UUID] = None
    reason: str
    description: Optional[str] = None
    status: str  # pending, reviewed, resolved, dismissed
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminReportListResponse(BaseModel):
    total: int
    reports: List[AdminReportResponse]


class AdminUpdateReportStatus(BaseModel):
    status: str  # reviewed, resolved, dismissed


# ---- Disputes ----
class AdminDisputeResponse(BaseModel):
    id: UUID
    ride_id: UUID
    host_id: UUID
    host_name: Optional[str] = None
    guest_id: UUID
    guest_name: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminDisputeListResponse(BaseModel):
    total: int
    disputes: List[AdminDisputeResponse]


class AdminUpdateDisputeStatus(BaseModel):
    status: str  # resolved, dismissed
    resolution_note: Optional[str] = None


# ---- Stats ----
class AdminStatsResponse(BaseModel):
    total_users: int
    active_rides: int
    completed_rides: int
    pending_reports: int
    open_disputes: int
    cancellation_rate: float


class CancellationStats(BaseModel):
    total_rides_created: int
    total_cancelled: int
    cancellation_rate: float
    daily_breakdown: Optional[dict] = None


# ---- Block/Unblock ----
class BlockUnblockResponse(BaseModel):
    user_id: UUID
    is_blocked: bool
    message: str


# ---- Unsafe Meetup Reports (stored as reports with reason='unsafe_meetup') ----
class AdminMeetupReportResponse(BaseModel):
    id: UUID
    reporter_id: UUID
    reporter_name: Optional[str] = None
    reported_user_id: UUID
    reported_user_name: Optional[str] = None
    match_id: Optional[UUID] = None
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminMeetupReportListResponse(BaseModel):
    total: int
    reports: List[AdminMeetupReportResponse]