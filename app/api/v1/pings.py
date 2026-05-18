from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional, List
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.ping_service import PingService
from app.schemas.ping import (
    RidePingCreate, RidePingUpdate,
    RidePingResponse, RidePingListResponse,
    RidePingNearbyListResponse, RidePingNearbyResponse,
)
from app.schemas.match import MatchRequestWithUserResponse, MatchRequestUserInfo
import uuid

router = APIRouter(prefix="/pings", tags=["Ride Pings"])


@router.post("", response_model=RidePingResponse, status_code=status.HTTP_201_CREATED)
async def create_ping(
    data: RidePingCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create a new ride ping."""
    service = PingService(db)
    ping = service.create_ping(uuid.UUID(user_id), data)
    return service.ping_to_response(ping)


@router.get("/nearby", response_model=RidePingNearbyListResponse)
async def get_nearby_pings(
    lat: float,
    lng: float,
    radius: float = 500.0,
    gender: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Find nearby open ride pings. Returns limited host profile (gender, rating, trust_level).

    Filters: status=open, within radius, not blocked, not expired, capacity available, gender compatible.
    """
    service = PingService(db)
    results = service.get_nearby_pings(
        lat=lat,
        lng=lng,
        current_user_id=uuid.UUID(user_id),
        radius_meters=radius,
        gender_preference=gender,
    )

    items = []
    for ping, distance in results:
        items.append(service.ping_to_nearby_response(ping, float(distance)))

    return {
        "total": len(items),
        "items": items,
    }


@router.get("/{ping_id}", response_model=RidePingResponse)
async def get_ping_details(
    ping_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get details of a specific ride ping."""
    service = PingService(db)
    ping = service.get_ping(ping_id)
    return service.ping_to_response(ping)


@router.patch("/{ping_id}", response_model=RidePingResponse)
async def update_ping(
    ping_id: uuid.UUID,
    data: RidePingUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update a ride ping."""
    service = PingService(db)
    ping = service.update_ping(ping_id, uuid.UUID(user_id), data)
    return service.ping_to_response(ping)


@router.post("/{ping_id}/cancel", response_model=RidePingResponse)
async def cancel_ping(
    ping_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Cancel a ride ping."""
    service = PingService(db)
    ping = service.cancel_ping(ping_id, uuid.UUID(user_id))
    return service.ping_to_response(ping)


@router.get("/{ping_id}/requests", response_model=List[MatchRequestWithUserResponse])
async def get_ping_requests(
    ping_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Host views all pending join requests for their ride.

    Returns guest info: id, name, gender, rating_avg.
    """
    service = PingService(db)
    requests = service.get_pending_requests_for_ride(ping_id, uuid.UUID(user_id))

    result = []
    for req in requests:
        guest_info = None
        if req.guest:
            guest_info = MatchRequestUserInfo(
                id=req.guest.id,
                name=req.guest.name,
                gender=req.guest.gender,
                rating_avg=req.guest.rating_avg,
            )
        result.append({
            "id": req.id,
            "ride_id": req.ride_id,
            "guest": guest_info,
            "status": req.status,
            "created_at": req.created_at,
        })
    return result