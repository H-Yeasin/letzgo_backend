from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class RatingCreate(BaseModel):
    match_id: UUID
    rated_user_id: UUID
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class RatingResponse(BaseModel):
    id: UUID
    match_id: UUID
    rater_id: UUID
    rated_user_id: UUID
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    reported_user_id: UUID
    match_id: Optional[UUID] = None
    reason: str
    description: Optional[str] = None


class ReportResponse(BaseModel):
    id: UUID
    reporter_id: UUID
    reported_user_id: UUID
    reason: str
    description: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
