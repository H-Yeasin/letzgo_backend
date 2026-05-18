import uuid
from sqlalchemy.orm import Session
from app.models.match import Match
from app.models.blocked_user import BlockedUser
from app.models.user import User
from app.core.exceptions import ForbiddenException, NotFoundException, ProfileIncompleteException


def check_profile_complete(user: User):
    """Ensure user has completed their profile."""
    if not user.is_onboarding_complete:
        raise ProfileIncompleteException()
    return user


def check_user_not_blocked(db: Session, current_user_id: uuid.UUID, target_user_id: uuid.UUID):
    """Check if current_user is blocked by target_user, or vice versa."""
    blocked = (
        db.query(BlockedUser)
        .filter(
            ((BlockedUser.blocker_id == target_user_id) & (BlockedUser.blocked_id == current_user_id)) |
            ((BlockedUser.blocker_id == current_user_id) & (BlockedUser.blocked_id == target_user_id))
        )
        .first()
    )
    if blocked:
        raise ForbiddenException(
            detail="Cannot interact with this user",
            code="USER_BLOCKED",
        )


def check_match_participant(match: Match, user_id: uuid.UUID):
    """Ensure the user is a participant in the match."""
    if match.host_id != user_id and match.guest_id != user_id:
        raise ForbiddenException(
            detail="You are not a participant in this match",
            code="NOT_MATCH_PARTICIPANT",
        )


def can_access_chat(db: Session, match_id: uuid.UUID, user_id: uuid.UUID) -> Match:
    """Verify user can access chat for this match."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise NotFoundException(detail="Match not found")
    check_match_participant(match, user_id)
    return match


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    """Get user or raise 404."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException(detail="User not found")
    return user