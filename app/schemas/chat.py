from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: UUID
    match_id: Optional[UUID] = None
    request_id: Optional[UUID] = None
    sender_id: UUID
    message: str
    created_at: datetime

    class Config:
        from_attributes = True