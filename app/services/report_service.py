import uuid
from sqlalchemy.orm import Session
from app.models.report import Report
from app.models.blocked_user import BlockedUser
from app.models.user import User
from app.core.exceptions import NotFoundException, BadRequestException
from app.schemas.rating_report import ReportCreate


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def create_report(self, reporter_id: uuid.UUID, data: ReportCreate) -> Report:
        if reporter_id == data.reported_user_id:
            raise BadRequestException(detail="Cannot report yourself")
            
        reported_user = self.db.query(User).filter(User.id == data.reported_user_id).first()
        if not reported_user:
            raise NotFoundException(detail="Reported user not found")

        report = Report(
            id=uuid.uuid4(),
            reporter_id=reporter_id,
            reported_user_id=data.reported_user_id,
            match_id=data.match_id,
            reason=data.reason,
            description=data.description,
            status="pending"
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def block_user(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID):
        if blocker_id == blocked_id:
            raise BadRequestException(detail="Cannot block yourself")
            
        existing = self.db.query(BlockedUser).filter(
            BlockedUser.blocker_id == blocker_id, 
            BlockedUser.blocked_id == blocked_id
        ).first()
        
        if not existing:
            block = BlockedUser(blocker_id=blocker_id, blocked_id=blocked_id)
            self.db.add(block)
            self.db.commit()
            
        return {"success": True, "message": "User blocked"}

    def unblock_user(self, blocker_id: uuid.UUID, blocked_id: uuid.UUID):
        block = self.db.query(BlockedUser).filter(
            BlockedUser.blocker_id == blocker_id, 
            BlockedUser.blocked_id == blocked_id
        ).first()
        if block:
            self.db.delete(block)
            self.db.commit()
        return {"success": True, "message": "User unblocked"}
