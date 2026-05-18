from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.report_service import ReportService
from app.schemas.rating_report import ReportCreate, ReportResponse
import uuid

router = APIRouter(prefix="/reports", tags=["Reports & Safety"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Report a user for safety or policy violations."""
    service = ReportService(db)
    return service.create_report(uuid.UUID(user_id), data)


@router.post("/block/{target_user_id}", status_code=status.HTTP_200_OK)
async def block_user(
    target_user_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Block a user from interacting with you."""
    service = ReportService(db)
    return service.block_user(uuid.UUID(user_id), target_user_id)
