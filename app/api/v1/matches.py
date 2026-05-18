from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.match_service import MatchService
from app.schemas.match import (
    MatchRequestCreate, MatchRequestResponse,
    MatchResponse, MatchDetailResponse, MatchCompleteRequest,
)
import uuid

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.post("/request", response_model=MatchRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_match_request(
    data: MatchRequestCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Guest requests to join a ride ping."""
    service = MatchService(db)
    return service.request_join(data.ride_id, uuid.UUID(user_id))


@router.post("/request/{request_id}/accept", response_model=MatchResponse)
async def accept_match_request(
    request_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Host accepts a match request."""
    service = MatchService(db)
    return service.accept_request(request_id, uuid.UUID(user_id))


@router.post("/request/{request_id}/decline", status_code=status.HTTP_200_OK)
async def decline_match_request(
    request_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Host declines a match request."""
    service = MatchService(db)
    service.decline_request(request_id, uuid.UUID(user_id))
    return {"success": True, "message": "Request declined"}


@router.get("", response_model=List[MatchResponse])
async def get_my_matches(
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get all matches for the current user."""
    service = MatchService(db)
    return service.get_user_matches(uuid.UUID(user_id), status)


@router.get("/{match_id}", response_model=MatchDetailResponse)
async def get_match_detail(
    match_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get details of a specific match."""
    service = MatchService(db)
    return service.get_match_detail(match_id)


@router.post("/{match_id}/start", response_model=MatchResponse)
async def start_ride(
    match_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Host marks the ride as started."""
    service = MatchService(db)
    return service.start_ride(match_id, uuid.UUID(user_id))


@router.post("/{match_id}/complete", response_model=MatchResponse)
async def complete_ride(
    match_id: uuid.UUID,
    data: MatchCompleteRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Host marks the ride as completed."""
    service = MatchService(db)
    return service.complete_ride(match_id, uuid.UUID(user_id))