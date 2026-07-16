import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from app.models.ride_ping import RidePing
from app.models.match_request import MatchRequest
from app.models.match import Match
from app.models.user import User
from app.models.blocked_user import BlockedUser
from app.core.constants import (
    PING_STATUS_OPEN, PING_STATUS_MATCHED,
    REQUEST_STATUS_PENDING, REQUEST_STATUS_ACCEPTED, REQUEST_STATUS_DECLINED, REQUEST_STATUS_CANCELLED,
    MATCH_STATUS_MATCHED, MATCH_STATUS_IN_PROGRESS, MATCH_STATUS_COMPLETED, MATCH_STATUS_CANCELLED, MATCH_STATUS_DISPUTED,
)
from app.core.exceptions import (
    NotFoundException, ForbiddenException, BadRequestException,
    ConflictException, UserBlockedException, RideAlreadyMatchedException,
    RideExpiredException, ProfileIncompleteException,
)
from app.services.ride_state_service import RideStateMachine
from app.core.permissions import check_profile_complete, check_user_not_blocked
from app.services.notification_service import NotificationService


class MatchService:
    def __init__(self, db: Session):
        self.db = db

    def request_join(self, ride_id: uuid.UUID, guest_id: uuid.UUID) -> MatchRequest:
        """Send a join request for a ride ping."""
        ride = self.db.query(RidePing).options(joinedload(RidePing.host)).filter(RidePing.id == ride_id).first()
        if not ride:
            raise NotFoundException(detail="Ride ping not found")

        # Validate host exists and profile is complete
        check_profile_complete(ride.host)

        # Cannot request your own ride
        if ride.host_id == guest_id:
            raise BadRequestException(detail="Cannot request to join your own ride")

        # Check ride is open
        if ride.status != PING_STATUS_OPEN:
            raise RideAlreadyMatchedException()

        # Check ride not expired
        if ride.expires_at and ride.expires_at < datetime.now(timezone.utc):
            raise RideExpiredException()

        # Check guest profile is complete
        guest = self.db.query(User).filter(User.id == guest_id).first()
        if not guest or not guest.is_onboarding_complete:
            raise ProfileIncompleteException()

        # Check blocked users
        check_user_not_blocked(self.db, guest_id, ride.host_id)

        # --- NEW: Gender join rule check ---
        pref = ride.gender_preference
        if pref == "male_only" and guest.gender != "male":
            raise BadRequestException(detail="This ride requires male guests only")
        if pref == "female_only" and guest.gender != "female":
            raise BadRequestException(detail="This ride requires female guests only")
        if pref == "male" and guest.gender != "male":
            raise BadRequestException(detail="This ride requires male guests only")
        if pref == "female" and guest.gender != "female":
            raise BadRequestException(detail="This ride requires female guests only")

        # --- NEW: Capacity check ---
        if (ride.current_passengers or 0) >= ride.max_passengers:
            raise BadRequestException(detail="This ride is already full")

        # Check existing active request
        existing = (
            self.db.query(MatchRequest)
            .filter(
                MatchRequest.ride_id == ride_id,
                MatchRequest.guest_id == guest_id,
                MatchRequest.status == REQUEST_STATUS_PENDING,
            )
            .first()
        )
        if existing:
            raise ConflictException(detail="Join request already sent")

        # Check existing active match
        existing_match = (
            self.db.query(Match)
            .filter(
                Match.ride_id == ride_id,
                Match.guest_id == guest_id,
                Match.status.in_([MATCH_STATUS_MATCHED, MATCH_STATUS_IN_PROGRESS]),
            )
            .first()
        )
        if existing_match:
            raise ConflictException(detail="Already matched on this ride")

        # Create request
        match_request = MatchRequest(
            id=uuid.uuid4(),
            ride_id=ride_id,
            guest_id=guest_id,
            host_id=ride.host_id,
            status=REQUEST_STATUS_PENDING,
        )
        self.db.add(match_request)
        self.db.commit()
        self.db.refresh(match_request)
        guest_name = guest.name if guest and guest.name else "A rider"
        NotificationService(self.db).create_notification(
            user_id=ride.host_id,
            title="New join request",
            body=f"{guest_name} requested to join your ride.",
            n_type="match_request",
            data={"related_id": str(ride.id), "request_id": str(match_request.id)},
        )
        return match_request

    def get_pending_requests(self, user_id: uuid.UUID) -> list:
        """Get pending join requests for user's rides."""
        requests = (
            self.db.query(MatchRequest)
            .options(joinedload(MatchRequest.ride))
            .filter(
                (MatchRequest.host_id == user_id) | (MatchRequest.guest_id == user_id),
                MatchRequest.status == REQUEST_STATUS_PENDING,
            )
            .order_by(MatchRequest.created_at.desc())
            .all()
        )
        return requests

    def accept_request(self, request_id: uuid.UUID, host_id: uuid.UUID) -> Match:
        """Accept a join request (host only). Idempotent - safe to call multiple times."""
        try:
            # 1. LOCK ONLY MAIN TABLE (NO JOINS)
            match_request = (
                self.db.query(MatchRequest)
                .filter(MatchRequest.id == request_id)
                .with_for_update(of=MatchRequest)
                .first()
            )

            if not match_request:
                raise NotFoundException(detail="Join request not found")

            # 2. AUTH CHECK
            if match_request.host_id != host_id:
                raise ForbiddenException(detail="Only the host can accept requests")

            # 3. STATE VALIDATION (idempotent safe)
            if match_request.status == REQUEST_STATUS_ACCEPTED:
                # Already accepted - return existing match (idempotent behavior)
                existing_match = (
                    self.db.query(Match)
                    .filter(
                        Match.ride_id == match_request.ride_id,
                        Match.guest_id == match_request.guest_id,
                        Match.status.in_([MATCH_STATUS_MATCHED, MATCH_STATUS_IN_PROGRESS]),
                    )
                    .first()
                )
                if existing_match:
                    self.db.rollback()
                    return existing_match
                # Edge case: request marked accepted but no match exists - fall through to create

            if match_request.status != REQUEST_STATUS_PENDING:
                raise BadRequestException(
                    detail=f"Cannot transition from '{match_request.status}' to 'accepted'"
                )

            # 4. UPDATE STATE
            # Ride must still be open
            ride = (
                self.db.query(RidePing)
                .filter(RidePing.id == match_request.ride_id)
                .with_for_update(of=RidePing)
                .first()
            )
            if not ride or ride.status != PING_STATUS_OPEN:
                raise RideAlreadyMatchedException()

            # Re-check capacity before accepting
            if (ride.current_passengers or 0) >= ride.max_passengers:
                raise BadRequestException(detail="This ride is already full")

            # Validate state machine transition
            RideStateMachine.transition_request(match_request.status, REQUEST_STATUS_ACCEPTED)

            match_request.status = REQUEST_STATUS_ACCEPTED

            # Update ping status and increment
            new_count = (ride.current_passengers or 0) + 1
            ride.current_passengers = new_count
            is_full = new_count >= ride.max_passengers
            ride.status = PING_STATUS_MATCHED if is_full else PING_STATUS_OPEN

            # Create match
            match = Match(
                id=uuid.uuid4(),
                request_id=match_request.id,
                ride_id=match_request.ride_id,
                host_id=match_request.host_id,
                guest_id=match_request.guest_id,
                status=MATCH_STATUS_MATCHED,
            )
            self.db.add(match)

            # Decline all other pending requests only if ride is now full
            if is_full:
                other_requests = (
                    self.db.query(MatchRequest)
                    .filter(
                        MatchRequest.ride_id == match_request.ride_id,
                        MatchRequest.status == REQUEST_STATUS_PENDING,
                        MatchRequest.id != request_id,
                    )
                    .all()
                )
                for req in other_requests:
                    req.status = REQUEST_STATUS_DECLINED

            # 5. COMMIT
            self.db.commit()
            self.db.refresh(match_request)
            self.db.refresh(match)

            # 6. OPTIONAL: LOAD RELATIONS AFTERWARD / NOTIFICATIONS
            NotificationService(self.db).create_notification(
                user_id=match_request.guest_id,
                title="Request accepted",
                body="Your join request was accepted.",
                n_type="match_accepted",
                data={"related_id": str(match_request.ride_id), "match_id": str(match.id)},
            )
            return match

        except Exception as e:
            self.db.rollback()
            # Re-raise application exceptions
            if isinstance(e, (NotFoundException, ForbiddenException, BadRequestException, RideAlreadyMatchedException)):
                raise
            raise HTTPException(status_code=500, detail="Internal server error")

    def decline_request(self, request_id: uuid.UUID, host_id: uuid.UUID) -> MatchRequest:
        """Decline a join request (host only). Idempotent - safe to call multiple times."""
        try:
            # 1. LOCK ONLY MAIN TABLE (NO JOINS)
            match_request = (
                self.db.query(MatchRequest)
                .filter(MatchRequest.id == request_id)
                .with_for_update(of=MatchRequest)
                .first()
            )

            if not match_request:
                raise NotFoundException(detail="Join request not found")

            # 2. AUTH CHECK
            if match_request.host_id != host_id:
                raise ForbiddenException(detail="Only the host can decline requests")

            # 3. STATE VALIDATION (idempotent safe)
            if match_request.status == REQUEST_STATUS_DECLINED:
                # Already declined - return as-is (idempotent behavior)
                self.db.rollback()
                return match_request

            if match_request.status != REQUEST_STATUS_PENDING:
                raise BadRequestException(
                    detail=f"Cannot transition from '{match_request.status}' to 'declined'"
                )

            # Validate state machine transition
            RideStateMachine.transition_request(match_request.status, REQUEST_STATUS_DECLINED)

            # 4. UPDATE STATE
            match_request.status = REQUEST_STATUS_DECLINED

            # 5. COMMIT
            self.db.commit()
            self.db.refresh(match_request)

            # 6. NOTIFICATIONS
            NotificationService(self.db).create_notification(
                user_id=match_request.guest_id,
                title="Request declined",
                body="Your join request was declined.",
                n_type="match_declined",
                data={"related_id": str(match_request.ride_id), "request_id": str(match_request.id)},
            )
            return match_request

        except Exception as e:
            self.db.rollback()
            # Re-raise application exceptions
            if isinstance(e, (NotFoundException, ForbiddenException, BadRequestException)):
                raise
            raise HTTPException(status_code=500, detail="Internal server error")

    def cancel_match(self, match_id: uuid.UUID, user_id: uuid.UUID) -> Match:
        """Cancel a match (participant only)."""
        match = self.db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise NotFoundException(detail="Match not found")

        if match.host_id != user_id and match.guest_id != user_id:
            raise ForbiddenException(detail="Only match participants can cancel")

        RideStateMachine.transition_match(match.status, MATCH_STATUS_CANCELLED)
        match.status = MATCH_STATUS_CANCELLED

        # Re-open the ride ping if it was matched
        ride = self.db.query(RidePing).filter(RidePing.id == match.ride_id).first()
        # --- NEW: Decrement current_passengers ---
        if ride and (ride.current_passengers or 0) > 0:
            ride.current_passengers -= 1
            if ride.status == PING_STATUS_MATCHED and ride.current_passengers < ride.max_passengers:
                ride.status = PING_STATUS_OPEN

        self.db.commit()
        self.db.refresh(match)
        return match

    def start_ride(self, match_id: uuid.UUID, user_id: uuid.UUID) -> Match:
        """Start a ride (host only)."""
        match = self.db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise NotFoundException(detail="Match not found")

        if match.host_id != user_id:
            raise ForbiddenException(detail="Only the host can start the ride")

        RideStateMachine.transition_match(match.status, MATCH_STATUS_IN_PROGRESS)
        match.status = MATCH_STATUS_IN_PROGRESS
        match.started_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(match)
        return match

    def complete_ride(self, match_id: uuid.UUID, user_id: uuid.UUID, final_fare: float = None) -> Match:
        """Complete a ride (host only)."""
        match = self.db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise NotFoundException(detail="Match not found")

        if match.host_id != user_id:
            raise ForbiddenException(detail="Only the host can complete the ride")

        RideStateMachine.transition_match(match.status, MATCH_STATUS_COMPLETED)
        match.status = MATCH_STATUS_COMPLETED
        match.completed_at = datetime.now(timezone.utc)

        # Set final fare on the ride ping
        ride = self.db.query(RidePing).filter(RidePing.id == match.ride_id).first()
        if ride and final_fare is not None:
            ride.final_fare = final_fare

        self.db.commit()
        self.db.refresh(match)
        return match

    def get_user_matches(self, user_id: uuid.UUID, status: str = None) -> list:
        """Get all matches for a user."""
        query = self.db.query(Match).filter(
            (Match.host_id == user_id) | (Match.guest_id == user_id)
        )
        if status:
            query = query.filter(Match.status == status)
        matches = query.order_by(Match.created_at.desc()).all()
        return matches

    def get_match_detail(self, match_id: uuid.UUID) -> Match:
        """Get match with related data."""
        match = (
            self.db.query(Match)
            .options(joinedload(Match.ride))
            .filter(Match.id == match_id)
            .first()
        )
        if not match:
            raise NotFoundException(detail="Match not found")
        return match

    def get_match_by_id(self, match_id: uuid.UUID) -> Match:
        """Get a match by ID."""
        match = self.db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise NotFoundException(detail="Match not found")
        return match

    def get_ride_passengers(self, ride_id: uuid.UUID, user_id: uuid.UUID) -> list:
        """Get the passengers for a given ride. Only accessible by the host or an accepted passenger."""
        ride = self.db.query(RidePing).filter(RidePing.id == ride_id).first()
        if not ride:
            raise NotFoundException(detail="Ride ping not found")

        # Get all matches for this ride
        matches = (
            self.db.query(Match)
            .options(joinedload(Match.guest))
            .filter(Match.ride_id == ride_id)
            .filter(Match.status.in_([MATCH_STATUS_MATCHED, MATCH_STATUS_IN_PROGRESS, MATCH_STATUS_COMPLETED]))
            .all()
        )

        # Check authorization: user must be the host, or one of the matched guests
        is_host = ride.host_id == user_id
        is_passenger = any(m.guest_id == user_id for m in matches)

        if not (is_host or is_passenger):
            raise ForbiddenException(detail="Only the host or accepted passengers can view the passenger list")

        return matches
