import uuid
import json
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.device_token import DeviceToken
from app.core.exceptions import NotFoundException


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def register_device_token(self, user_id: uuid.UUID, token: str, platform: str):
        existing = self.db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id, 
            DeviceToken.token == token
        ).first()
        if not existing:
            new_token = DeviceToken(user_id=user_id, token=token, platform=platform)
            self.db.add(new_token)
            self.db.commit()
            return new_token
        return existing

    def unregister_device_token(self, user_id: uuid.UUID, token: str):
        existing = self.db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id, 
            DeviceToken.token == token
        ).first()
        if existing:
            self.db.delete(existing)
            self.db.commit()

    def create_notification(self, user_id: uuid.UUID, title: str, body: str, n_type: str = "general", data: dict = None):
        notif = Notification(
            user_id=user_id,
            title=title,
            body=body,
            type=n_type,
            data=json.dumps(data) if data else None
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)
        
        # Here you would typically also trigger a push notification via FCM
        return notif

    def get_user_notifications(self, user_id: uuid.UUID, limit: int = 50, unread_only: bool = False):
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read == False)
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def get_unread_count(self, user_id: uuid.UUID):
        from sqlalchemy import func
        return self.db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id, 
            Notification.is_read == False
        ).scalar()

    def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID):
        notif = self.db.query(Notification).filter(
            Notification.id == notification_id, 
            Notification.user_id == user_id
        ).first()
        if not notif:
            raise NotFoundException(detail="Notification not found")
        notif.is_read = True
        self.db.commit()
        self.db.refresh(notif)
        return notif

    def mark_all_as_read(self, user_id: uuid.UUID):
        self.db.query(Notification).filter(
            Notification.user_id == user_id, 
            Notification.is_read == False
        ).update({"is_read": True})
        self.db.commit()
