from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.notification_service import NotificationService
from app.schemas.notification import DeviceTokenCreate, NotificationResponse, NotificationListResponse
import uuid

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/device-token", status_code=status.HTTP_200_OK)
async def register_device_token(
    data: DeviceTokenCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Register a device token for push notifications."""
    service = NotificationService(db)
    service.register_device_token(uuid.UUID(user_id), data.token, data.platform)
    return {"success": True, "message": "Token registered"}


@router.get("", response_model=NotificationListResponse)
async def get_my_notifications(
    limit: int = 50,
    unread_only: bool = False,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get notifications for the current user."""
    service = NotificationService(db)
    notifications = service.get_user_notifications(uuid.UUID(user_id), limit, unread_only)
    unread_count = service.get_unread_count(uuid.UUID(user_id))
    return {
        "items": notifications,
        "unread_count": unread_count
    }


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    service = NotificationService(db)
    return service.mark_as_read(notification_id, uuid.UUID(user_id))


@router.post("/read-all")
async def mark_all_notifications_read(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read."""
    service = NotificationService(db)
    service.mark_all_as_read(uuid.UUID(user_id))
    return {"success": True, "message": "All notifications marked as read"}
