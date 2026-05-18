from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.rating_service import RatingService
from app.schemas.rating_report import RatingCreate, RatingResponse
import uuid

router = APIRouter(prefix="/ratings", tags=["Ratings"])


@router.post("", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def create_rating(
    data: RatingCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Rate another user after a match."""
    service = RatingService(db)
    return service.create_rating(uuid.UUID(user_id), data)
