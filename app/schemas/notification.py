from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class DeviceTokenCreate(BaseModel):
    token: str
    platform: Optional[str] = "android"


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    body: str
    data: Optional[str] = None
    type: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    unread_count: int
