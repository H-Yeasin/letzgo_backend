import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user_id
from app.models.match import Match
from app.core.exceptions import NotFoundException, ForbiddenException


router = APIRouter()


@router.post("/{match_id}/split")
async def request_fare_split(
    match_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Request a fare split for a match."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise NotFoundException(detail="Match not found")
        
    if match.host_id != current_user_id and match.guest_id != current_user_id:
        raise ForbiddenException(detail="Not part of this match")
        
    # Logic for fare splitting (e.g. creating a record, notifying the other party)
    # For MVP, we just mark it as split requested
    return {"status": "success", "message": "Fare split requested"}


@router.get("/{match_id}/summary")
async def get_fare_summary(
    match_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Get the fare summary for a completed match."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise NotFoundException(detail="Match not found")
        
    return {
        "match_id": match_id,
        "total_fare": 0.0, # Placeholder
        "split_fare": 0.0,
        "status": match.status
    }