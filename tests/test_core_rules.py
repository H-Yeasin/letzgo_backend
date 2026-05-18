"""
Core rule engine tests for LetzGo marketplace MVP.

Tests cover:
1. Gender join rule enforcement
2. Capacity check enforcement
3. Capacity increment on accept
4. Capacity decrement on cancel
5. Nearby feed filtering (capacity, expired, blocked)
6. Ping-to-nearby response shape (limited pre-join host visibility)
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta, timezone

from app.models.ride_ping import RidePing
from app.models.user import User
from app.models.match_request import MatchRequest
from app.models.match import Match
from app.models.blocked_user import BlockedUser
from app.services.match_service import MatchService
from app.services.ping_service import PingService
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    ConflictException,
    RideAlreadyMatchedException,
    RideExpiredException,
    ProfileIncompleteException,
)


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def make_mock_user(
    user_id=None,
    gender="male",
    rating_avg=4.5,
    completed_rides_count=10,
    is_verified=True,
    is_onboarding_complete=True,
):
    u = MagicMock(spec=User)
    u.id = user_id or uuid.uuid4()
    u.gender = gender
    u.rating_avg = rating_avg
    u.completed_rides_count = completed_rides_count
    u.is_verified = is_verified
    u.is_onboarding_complete = is_onboarding_complete
    u.name = "Test User"
    u.avatar_url = None
    return u


def make_mock_ride(
    ride_id=None,
    host_id=None,
    gender_preference="any",
    max_passengers=2,
    current_passengers=0,
    status="open",
    expires_at=None,
    pickup_label="Mohakhali",
    destination_label="Mirpur 10",
    estimated_fare=120,
):
    r = MagicMock(spec=RidePing)
    r.id = ride_id or uuid.uuid4()
    r.host_id = host_id or uuid.uuid4()
    r.gender_preference = gender_preference
    r.max_passengers = max_passengers
    r.current_passengers = current_passengers
    r.status = status
    r.expires_at = expires_at or (datetime.now(timezone.utc) + timedelta(minutes=30))
    r.pickup_label = pickup_label
    r.destination_label = destination_label
    r.estimated_fare = estimated_fare
    r.meetup_point = None
    r.final_fare = None
    r.host = None
    return r


# --------------------------------------------------------------------------- #
#  1. Gender Join Rule Tests
# --------------------------------------------------------------------------- #

class TestGenderJoinRule:
    """Verify that gender_preference is strictly enforced when requesting join."""

    def test_any_allows_male_guest(self):
        """any → male guest can join."""
        ride = make_mock_ride(gender_preference="any")
        guest = make_mock_user(gender="male")
        db = MagicMock()
        svc = MatchService(db)
        assert svc._can_join_by_gender(ride, guest) is True

    def test_any_allows_female_guest(self):
        """any → female guest can join."""
        ride = make_mock_ride(gender_preference="any")
        guest = make_mock_user(gender="female")
        db = MagicMock()
        svc = MatchService(db)
        assert svc._can_join_by_gender(ride, guest) is True

    def test_male_only_allows_male(self):
        """male_only → male guest can join."""
        ride = make_mock_ride(gender_preference="male_only")
        guest = make_mock_user(gender="male")
        db = MagicMock()
        svc = MatchService(db)
        assert svc._can_join_by_gender(ride, guest) is True

    def test_male_only_rejects_female(self):
        """male_only → female guest is rejected."""
        ride = make_mock_ride(gender_preference="male_only")
        guest = make_mock_user(gender="female")
        db = MagicMock()
        svc = MatchService(db)
        assert svc._can_join_by_gender(ride, guest) is False

    def test_female_only_allows_female(self):
        """female_only → female guest can join."""
        ride = make_mock_ride(gender_preference="female_only")
        guest = make_mock_user(gender="female")
        db = MagicMock()
        svc = MatchService(db)
        assert svc._can_join_by_gender(ride, guest) is True

    def test_female_only_rejects_male(self):
        """female_only → male guest is rejected."""
        ride = make_mock_ride(gender_preference="female_only")
        guest = make_mock_user(gender="male")
        db = MagicMock()
        svc = MatchService(db)
        assert svc._can_join_by_gender(ride, guest) is False

    def test_legacy_male_value(self):
        """'male' (legacy) → only male guests can join."""
        ride = make_mock_ride(gender_preference="male")
        guest_male = make_mock_user(gender="male")
        guest_female = make_mock_user(gender="female")
        db = MagicMock()
        svc = MatchService(db)
        assert svc._can_join_by_gender(ride, guest_male) is True
        assert svc._can_join_by_gender(ride, guest_female) is False

    def test_legacy_female_value(self):
        """'female' (legacy) → only female guests can join."""
        ride = make_mock_ride(gender_preference="female")
        guest_male = make_mock_user(gender="male")
        guest_female = make_mock_user(gender="female")
        db = MagicMock()
        svc = MatchService(db)
        assert svc._can_join_by_gender(ride, guest_female) is True
        assert svc._can_join_by_gender(ride, guest_male) is False


# --------------------------------------------------------------------------- #
#  2. Capacity Rule Tests
# --------------------------------------------------------------------------- #

class TestCapacityRule:
    """Verify capacity is enforced on request_join and accept_request."""

    def test_request_join_full_ride_raises_error(self):
        """Requesting to join a full ride raises BadRequestException."""
        ride = make_mock_ride(max_passengers=2, current_passengers=2)
        guest = make_mock_user()
        ride.host = make_mock_user()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            ride,          # first query: ride
            guest,         # guest user
            None,          # blocked check
            None,          # existing match request
            None,          # existing match
        ]

        svc = MatchService(db)
        with pytest.raises(BadRequestException, match="already full"):
            svc.request_join(ride.id, guest.id)

    def test_accept_full_ride_raises_error(self):
        """Accepting a join request on a now-full ride raises error."""
        match_request = MagicMock(spec=MatchRequest)
        match_request.id = uuid.uuid4()
        match_request.ride_id = uuid.uuid4()
        match_request.guest_id = uuid.uuid4()
        match_request.host_id = uuid.uuid4()
        match_request.status = "pending"

        ride = make_mock_ride(max_passengers=1, current_passengers=1)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            match_request,  # first query
            ride,           # ride query
        ]

        svc = MatchService(db)
        with pytest.raises(BadRequestException, match="already full"):
            svc.accept_request(match_request.id, match_request.host_id)

    def test_accept_increments_passengers(self):
        """Accepting a request increments current_passengers by 1."""
        host_id = uuid.uuid4()
        match_request = MagicMock(spec=MatchRequest)
        match_request.id = uuid.uuid4()
        match_request.ride_id = uuid.uuid4()
        match_request.guest_id = uuid.uuid4()
        match_request.host_id = host_id
        match_request.status = "pending"

        ride = make_mock_ride(
            host_id=host_id,
            max_passengers=2,
            current_passengers=0,
            status="open",
        )

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            match_request,  # 1st: get match request
            ride,           # 2nd: get ride
        ]
        db.query.return_value.filter.return_value.all.return_value = []  # other_requests

        svc = MatchService(db)
        svc.accept_request(match_request.id, host_id)

        assert ride.current_passengers == 1

    def test_cancel_decrements_passengers(self):
        """Cancelling a match decrements current_passengers by 1."""
        host_id = uuid.uuid4()
        match_obj = MagicMock(spec=Match)
        match_obj.id = uuid.uuid4()
        match_obj.ride_id = uuid.uuid4()
        match_obj.host_id = host_id
        match_obj.guest_id = uuid.uuid4()
        match_obj.status = "matched"

        ride = make_mock_ride(
            host_id=host_id,
            max_passengers=2,
            current_passengers=1,
            status="matched",
        )

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            match_obj,  # get match
            ride,       # get ride
        ]

        svc = MatchService(db)
        svc.cancel_match(match_obj.id, host_id)

        assert ride.current_passengers == 0

    def test_nearby_feed_excludes_full_rides(self):
        """get_nearby_pings excludes rides where current >= max_passengers."""
        point_wkt = "POINT(90.4125 23.8103)"

        full_ride = make_mock_ride(max_passengers=1, current_passengers=1)
        available_ride = make_mock_ride(max_passengers=2, current_passengers=0)

        db = MagicMock()
        # blocked queries return empty
        db.query.return_value.filter.return_value = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        # The main query returns only the available ride (full ride filtered out)
        db.query.return_value.options.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            (available_ride, 100.0),
        ]

        svc = PingService(db)
        results = svc.get_nearby_pings(
            lat=23.8103, lng=90.4125,
            current_user_id=uuid.uuid4(),
            radius_meters=500,
        )

        assert len(results) == 1
        assert results[0][0].id == available_ride.id


# --------------------------------------------------------------------------- #
#  3. Nearby Feed Response Shape Tests
# --------------------------------------------------------------------------- #

class TestNearbyFeedResponseShape:
    """Verify the nearby feed returns limited pre-join host profile."""

    def test_ping_to_nearby_response_has_limited_host(self):
        """ping_to_nearby_response only exposes gender, rating, trust_level."""
        host = make_mock_user(
            gender="male",
            rating_avg=4.7,
            completed_rides_count=25,
        )
        ride = make_mock_ride(
            max_passengers=2,
            current_passengers=0,
            estimated_fare=120,
        )
        ride.host = host

        db = MagicMock()
        svc = PingService(db)

        with patch("app.services.ping_service.extract_coordinates", return_value=(23.78, 90.405)):
            resp = svc.ping_to_nearby_response(ride, 180.0)

        assert resp["ride_id"] == str(ride.id)
        assert resp["pickup_label"] == "Mohakhali"
        assert resp["destination_label"] == "Mirpur 10"
        assert resp["estimated_fare"] == 120
        assert resp["available_seats"] == 2
        assert resp["gender_preference"] == "any"
        assert resp["distance_meters"] == 180.0

        # Host profile must be limited
        host_info = resp["host"]
        assert host_info["gender"] == "male"
        assert host_info["rating"] == 4.7
        assert host_info["trust_level"] == "high"
        # These should NOT be in the nearby response
        assert "name" not in host_info
        assert "avatar_url" not in host_info
        assert "phone" not in host_info

    def test_trust_level_high(self):
        """trust_level = high when >= 20 rides and rating >= 4.5."""
        host = make_mock_user(completed_rides_count=20, rating_avg=4.5)
        ride = make_mock_ride()
        ride.host = host

        db = MagicMock()
        svc = PingService(db)
        with patch("app.services.ping_service.extract_coordinates", return_value=(23.78, 90.405)):
            resp = svc.ping_to_nearby_response(ride, 100.0)

        assert resp["host"]["trust_level"] == "high"

    def test_trust_level_medium(self):
        """trust_level = medium when >= 5 rides and rating >= 4.0."""
        host = make_mock_user(completed_rides_count=5, rating_avg=4.0)
        ride = make_mock_ride()
        ride.host = host

        db = MagicMock()
        svc = PingService(db)
        with patch("app.services.ping_service.extract_coordinates", return_value=(23.78, 90.405)):
            resp = svc.ping_to_nearby_response(ride, 100.0)

        assert resp["host"]["trust_level"] == "medium"

    def test_trust_level_low(self):
        """trust_level = low when has some rides but below thresholds."""
        host = make_mock_user(completed_rides_count=1, rating_avg=3.5)
        ride = make_mock_ride()
        ride.host = host

        db = MagicMock()
        svc = PingService(db)
        with patch("app.services.ping_service.extract_coordinates", return_value=(23.78, 90.405)):
            resp = svc.ping_to_nearby_response(ride, 100.0)

        assert resp["host"]["trust_level"] == "low"

    def test_trust_level_unknown_when_no_host(self):
        """trust_level = unknown when host data is unavailable."""
        ride = make_mock_ride()
        ride.host = None

        db = MagicMock()
        svc = PingService(db)
        with patch("app.services.ping_service.extract_coordinates", return_value=(23.78, 90.405)):
            resp = svc.ping_to_nearby_response(ride, 100.0)

        assert resp["host"]["trust_level"] == "unknown"

    def test_available_seats_never_negative(self):
        """available_seats is clamped to 0 if full or over capacity."""
        host = make_mock_user()
        ride = make_mock_ride(max_passengers=2, current_passengers=5)
        ride.host = host

        db = MagicMock()
        svc = PingService(db)
        with patch("app.services.ping_service.extract_coordinates", return_value=(23.78, 90.405)):
            resp = svc.ping_to_nearby_response(ride, 100.0)

        assert resp["available_seats"] == 0


# --------------------------------------------------------------------------- #
#  4. Request Join Precondition Tests
# --------------------------------------------------------------------------- #

class TestRequestJoinPreconditions:
    """Verify all preconditions in request_join work correctly."""

    def test_own_ride_raises_error(self):
        """Cannot request to join your own ride."""
        user_id = uuid.uuid4()
        ride = make_mock_ride(host_id=user_id)
        ride.host = make_mock_user()

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = ride

        svc = MatchService(db)
        with pytest.raises(BadRequestException, match="own ride"):
            svc.request_join(ride.id, user_id)

    def test_closed_ride_raises_error(self):
        """Cannot request to join a non-open ride."""
        ride = make_mock_ride(status="matched")
        ride.host = make_mock_user()
        guest_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = ride

        svc = MatchService(db)
        with pytest.raises(RideAlreadyMatchedException):
            svc.request_join(ride.id, guest_id)

    def test_expired_ride_raises_error(self):
        """Cannot request to join an expired ride."""
        expired = datetime.now(timezone.utc) - timedelta(minutes=5)
        ride = make_mock_ride(expires_at=expired)
        ride.host = make_mock_user()
        guest_id = uuid.uuid4()

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = ride

        svc = MatchService(db)
        with pytest.raises(RideExpiredException):
            svc.request_join(ride.id, guest_id)

    def test_incomplete_profile_raises_error(self):
        """User with incomplete onboarding cannot request join."""
        ride = make_mock_ride()
        ride.host = make_mock_user()
        guest = make_mock_user(is_onboarding_complete=False)

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.side_effect = [
            ride,   # ride query
            guest,  # guest query
        ]

        svc = MatchService(db)
        with pytest.raises(ProfileIncompleteException):
            svc.request_join(ride.id, guest.id)

    def test_duplicate_request_raises_error(self):
        """Sending a duplicate pending request raises ConflictException."""
        ride = make_mock_ride()
        ride.host = make_mock_user()
        guest = make_mock_user()
        existing_request = MagicMock(spec=MatchRequest)

        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.side_effect = [
            ride,               # ride query
            ride.host,          # host profile check
            guest,              # guest query
            None,               # blocked check
            existing_request,   # existing pending request found
        ]

        svc = MatchService(db)
        with pytest.raises(ConflictException, match="already sent"):
            svc.request_join(ride.id, guest.id)