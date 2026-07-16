from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class FindRideRequest(BaseModel):
    current_lat: float = Field(..., ge=-90, le=90)
    current_lng: float = Field(..., ge=-180, le=180)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lng: float = Field(..., ge=-180, le=180)
    # Legacy single radius; used as fallback when the split radii are absent.
    radius: float = Field(default=500.0, ge=100, le=10000)
    pickup_radius: Optional[float] = Field(default=None, ge=100, le=10000)
    destination_radius: Optional[float] = Field(default=None, ge=100, le=10000)

    @property
    def effective_pickup_radius(self) -> float:
        return self.pickup_radius if self.pickup_radius is not None else self.radius

    @property
    def effective_destination_radius(self) -> float:
        return self.destination_radius if self.destination_radius is not None else self.radius