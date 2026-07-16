from fastapi import APIRouter, Depends, status
import logging
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session
from typing import Optional, List
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.core.config import settings
from app.services.ping_service import PingService
from app.schemas.ping import (
    RidePingCreate, RidePingUpdate,
    RidePingResponse, RidePingListResponse,
    DeleteExpiredPingsResponse,
)
from app.schemas.match import MatchRequestWithUserResponse, MatchRequestUserInfo
import uuid

router = APIRouter(prefix="/pings", tags=["Ride Pings"])
logger = logging.getLogger("app.pings")


def _safe_db_url(url: str) -> str:
    try:
        parsed = make_url(url)
        if parsed.password:
            parsed = parsed.set(password="***")
        return str(parsed)
    except Exception:
        return "<unparseable>"


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


@router.get("/me", response_model=RidePingListResponse)
async def get_my_pings(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List ride pings created by the authenticated host."""
    service = PingService(db)
    pings = service.get_pings_by_host(uuid.UUID(user_id))
    items = [service.ping_to_response(ping) for ping in pings]
    return {
        "total": len(items),
        "items": items,
    }


@router.delete("/expired", response_model=DeleteExpiredPingsResponse)
async def delete_expired_pings(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Remove expired pings owned by the authenticated host."""
    service = PingService(db)
    deleted = service.delete_expired_pings_for_host(uuid.UUID(user_id))
    return DeleteExpiredPingsResponse(deleted=deleted)


@router.get("/nearby", response_model=RidePingListResponse)
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
    logger.info(
        "nearby_pings request user=%s lat=%.6f lng=%.6f radius=%.1f gender=%s db=%s",
        user_id,
        lat,
        lng,
        radius,
        gender,
        _safe_db_url(settings.DATABASE_URL),
    )
    service = PingService(db)
    results = service.get_nearby_pings(
        lat=lat,
        lng=lng,
        current_user_id=uuid.UUID(user_id),
        radius_meters=radius,
        gender_preference=gender,
    )
    logger.info("nearby_pings result_count=%s user=%s", len(results), user_id)

    items = []
    for ping, _distance in results:
        items.append(service.ping_to_response(ping))

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


from app.schemas.ping import RidePassengerResponse

@router.get("/{ping_id}/passengers", response_model=List[RidePassengerResponse])
async def get_ping_passengers(
    ping_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get all matched passengers for a ride. Only host and passengers can view."""
    # Note: importing MatchService locally to avoid circular imports if any, but PingService is already used
    from app.services.match_service import MatchService
    service = MatchService(db)
    matches = service.get_ride_passengers(ping_id, uuid.UUID(user_id))

    result = []
    for m in matches:
        if m.guest:
            result.append(RidePassengerResponse(
                match_id=m.id,
                user_id=m.guest.id,
                name=m.guest.name,
                gender=m.guest.gender,
                rating_avg=m.guest.rating_avg,
            ))
    return result
