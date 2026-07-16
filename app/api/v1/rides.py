from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.ping_service import PingService
from app.schemas.ride import FindRideRequest
from app.schemas.ping import RidePingListResponse
import uuid

router = APIRouter(prefix="/rides", tags=["Rides"])


@router.post("/find", response_model=RidePingListResponse)
async def find_rides(
    data: FindRideRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Find rides headed near a user's desired destination.

    User sends their current location + destination.
    Returns rides where both pickup is near user AND destination is near user's destination.
    """
    service = PingService(db)
    results = service.find_rides(
        current_lat=data.current_lat,
        current_lng=data.current_lng,
        destination_lat=data.destination_lat,
        destination_lng=data.destination_lng,
        current_user_id=uuid.UUID(user_id),
        pickup_radius_meters=data.effective_pickup_radius,
        destination_radius_meters=data.effective_destination_radius,
    )

    items = []
    for ping, _distance in results:
        items.append(service.ping_to_response(ping))

    return {
        "total": len(items),
        "items": items,
    }
