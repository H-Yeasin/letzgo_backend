import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import create_access_token


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_phone(self, phone: str) -> User | None:
        return self.db.query(User).filter(User.phone == phone).first()

    def create_user(self, data: UserCreate) -> User:
        user = User(
            id=uuid.uuid4(),
            phone=data.phone,
            name=data.name or "User",
            gender=data.gender,
            avatar_url=data.avatar_url,
            fcm_token=data.fcm_token,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> User | None:
        user = self.get_by_id(user_id)
        if not user:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def generate_auth_response(self, user: User, is_new_user: bool = False):
        token = create_access_token(data={"sub": str(user.id)})
        from app.schemas.user import UserResponse, AuthResponse

        user_resp = UserResponse(
            id=user.id,
            phone=user.phone,
            name=user.name,
            gender=user.gender,
            avatar_url=user.avatar_url,
            rating_avg=user.rating_avg,
            completed_rides_count=user.completed_rides_count,
            is_verified=user.is_verified,
            is_onboarding_complete=user.is_onboarding_complete,
            created_at=user.created_at,
        )
        return AuthResponse(
            access_token=token,
            user=user_resp,
            is_new_user=is_new_user,
        )

    def update_rating(self, user_id: uuid.UUID):
        """Recalculate average rating for a user."""
        from app.models.rating import Rating
        avg = (
            self.db.query(func.avg(Rating.rating))
            .filter(Rating.reviewed_user_id == user_id)
            .scalar()
        )
        count = (
            self.db.query(func.count(Rating.id))
            .filter(Rating.reviewed_user_id == user_id)
            .scalar()
        )
        user = self.get_by_id(user_id)
        if user:
            user.rating_avg = round(avg or 0.0, 2)
            user.completed_rides_count = count or 0
            self.db.commit()