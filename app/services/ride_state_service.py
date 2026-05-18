"""
Ride State Machine — Centralizes all state transitions.
Ensures valid flows and prevents invalid transitions.
"""

from app.core.constants import (
    PING_STATUS_OPEN, PING_STATUS_MATCHED, PING_STATUS_CANCELLED, PING_STATUS_EXPIRED,
    REQUEST_STATUS_PENDING, REQUEST_STATUS_ACCEPTED, REQUEST_STATUS_DECLINED, REQUEST_STATUS_CANCELLED,
    MATCH_STATUS_MATCHED, MATCH_STATUS_IN_PROGRESS, MATCH_STATUS_COMPLETED, MATCH_STATUS_CANCELLED, MATCH_STATUS_DISPUTED,
)
from app.core.exceptions import InvalidStateTransitionException


class RideStateMachine:
    """Validates and executes ride state transitions."""

    # Allowed transitions for Ping statuses
    PING_TRANSITIONS = {
        PING_STATUS_OPEN: [PING_STATUS_MATCHED, PING_STATUS_CANCELLED, PING_STATUS_EXPIRED],
        PING_STATUS_MATCHED: [PING_STATUS_CANCELLED],
    }

    # Allowed transitions for Match Request statuses
    REQUEST_TRANSITIONS = {
        REQUEST_STATUS_PENDING: [REQUEST_STATUS_ACCEPTED, REQUEST_STATUS_DECLINED, REQUEST_STATUS_CANCELLED],
    }

    # Allowed transitions for Match statuses
    MATCH_TRANSITIONS = {
        MATCH_STATUS_MATCHED: [MATCH_STATUS_IN_PROGRESS, MATCH_STATUS_CANCELLED],
        MATCH_STATUS_IN_PROGRESS: [MATCH_STATUS_COMPLETED, MATCH_STATUS_DISPUTED],
        MATCH_STATUS_COMPLETED: [],  # Terminal state
        MATCH_STATUS_CANCELLED: [],  # Terminal state
        MATCH_STATUS_DISPUTED: [MATCH_STATUS_COMPLETED],  # Can resolve dispute to completed
    }

    @classmethod
    def can_transition_ping(cls, current: str, target: str) -> bool:
        """Check if a ping can transition from current to target state."""
        allowed = cls.PING_TRANSITIONS.get(current, [])
        return target in allowed

    @classmethod
    def can_transition_request(cls, current: str, target: str) -> bool:
        """Check if a match request can transition."""
        allowed = cls.REQUEST_TRANSITIONS.get(current, [])
        return target in allowed

    @classmethod
    def can_transition_match(cls, current: str, target: str) -> bool:
        """Check if a match can transition."""
        allowed = cls.MATCH_TRANSITIONS.get(current, [])
        return target in allowed

    @classmethod
    def transition_ping(cls, current: str, target: str) -> str:
        """Execute ping state transition or raise."""
        if not cls.can_transition_ping(current, target):
            raise InvalidStateTransitionException(current, target)
        return target

    @classmethod
    def transition_request(cls, current: str, target: str) -> str:
        """Execute match request state transition or raise."""
        if not cls.can_transition_request(current, target):
            raise InvalidStateTransitionException(current, target)
        return target

    @classmethod
    def transition_match(cls, current: str, target: str) -> str:
        """Execute match state transition or raise."""
        if not cls.can_transition_match(current, target):
            raise InvalidStateTransitionException(current, target)
        return target