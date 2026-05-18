from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class FindRideRequest(BaseModel):
    current_lat: float = Field(..., ge=-90, le=90)
    current_lng: float = Field(..., ge=-180, le=180)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lng: float = Field(..., ge=-180, le=180)
    radius: float = Field(default=500.0, ge=100, le=10000)