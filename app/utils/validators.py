import uuid
from typing import Optional
from app.core.constants import GENDERS, PING_STATUSES, MATCH_STATUSES, REPORT_REASONS


def validate_uuid(value: str) -> Optional[uuid.UUID]:
    """Validate and parse a UUID string."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


def validate_gender(value: str) -> str:
    """Validate gender value."""
    valid = {"any", "male", "female"}
    if value.lower() not in valid:
        raise ValueError(f"Invalid gender '{value}'. Must be one of: {', '.join(valid)}")
    return value.lower()


def validate_rating(value: int) -> int:
    """Validate rating is within 1-5 range."""
    if not (1 <= value <= 5):
        raise ValueError("Rating must be between 1 and 5")
    return value


def validate_phone(phone: str) -> str:
    """Basic phone number validation."""
    phone = phone.strip()
    if not phone:
        raise ValueError("Phone number is required")
    if len(phone) < 10 or len(phone) > 15:
        raise ValueError("Phone number must be between 10 and 15 digits")
    return phone


def validate_pagination(page: int, per_page: int):
    """Validate pagination parameters."""
    if page < 1:
        raise ValueError("Page must be >= 1")
    if per_page < 1 or per_page > 100:
        raise ValueError("Per page must be between 1 and 100")