from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    phone: str = Field(..., pattern=r"^\+?1?\d{10,15}$")
    name: Optional[str] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    fcm_token: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    fcm_token: Optional[str] = None
    is_onboarding_complete: Optional[bool] = None


class UserResponse(BaseModel):
    id: UUID
    phone: str
    name: str
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    rating_avg: float = 0.0
    completed_rides_count: int = 0
    is_verified: bool = False
    is_onboarding_complete: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserPublicProfile(BaseModel):
    """Profile visible to other users before matching."""
    id: UUID
    name: str
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    rating_avg: float = 0.0
    completed_rides_count: int = 0
    is_verified: bool = False

    class Config:
        from_attributes = True


class OTPRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+?1?\d{10,15}$")


class OTPVerify(BaseModel):
    phone: str = Field(..., pattern=r"^\+?1?\d{10,15}$")
    otp: str = Field(..., min_length=4, max_length=6)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool = False