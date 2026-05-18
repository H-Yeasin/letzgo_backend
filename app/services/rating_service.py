import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.rating import Rating
from app.models.user import User
from app.models.match import Match
from app.core.exceptions import NotFoundException, BadRequestException
from app.schemas.rating_report import RatingCreate


class RatingService:
    def __init__(self, db: Session):
        self.db = db

    def create_rating(self, rater_id: uuid.UUID, data: RatingCreate) -> Rating:
        # Verify match exists and is completed
        match = self.db.query(Match).filter(Match.id == data.match_id).first()
        if not match:
            raise NotFoundException(detail="Match not found")
        if match.status != "completed":
            raise BadRequestException(detail="Can only rate after a completed ride")

        # Verify rater was part of match
        if match.host_id != rater_id and match.guest_id != rater_id:
            raise BadRequestException(detail="You were not part of this match")

        # Check if already rated
        existing = self.db.query(Rating).filter(
            Rating.match_id == data.match_id, 
            Rating.rater_id == rater_id
        ).first()
        if existing:
            raise BadRequestException(detail="You have already rated this match")

        rating = Rating(
            id=uuid.uuid4(),
            match_id=data.match_id,
            rater_id=rater_id,
            rated_user_id=data.rated_user_id,
            rating=data.rating,
            comment=data.comment
        )
        self.db.add(rating)
        self.db.commit()
        self.db.refresh(rating)

        # Update average rating for the rated user
        self.update_user_rating_stats(data.rated_user_id)
        
        return rating

    def update_user_rating_stats(self, user_id: uuid.UUID):
        stats = self.db.query(
            func.avg(Rating.rating).label("avg_rating"),
            func.count(Rating.id).label("total_ratings")
        ).filter(Rating.rated_user_id == user_id).first()

        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.rating_avg = float(stats.avg_rating) if stats.avg_rating else 0.0
            # Note: completed_rides_count is usually updated by the match completion logic
            self.db.commit()
