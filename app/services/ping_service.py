import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, cast
from geoalchemy2 import Geometry, Geography, functions as geo_func
from app.models.ride_ping import RidePing
from app.models.match_request import MatchRequest
from app.models.user import User
from app.models.blocked_user import BlockedUser
from app.core.constants import (
    PING_STATUS_OPEN, PING_STATUS_CANCELLED, PING_STATUS_EXPIRED,
    DEFAULT_SEARCH_RADIUS_METERS, EXPANDED_SEARCH_RADIUS_METERS,
    DEFAULT_FIND_PICKUP_RADIUS_METERS, DEFAULT_FIND_DESTINATION_RADIUS_METERS,
    GENDER_ANY, GENDER_MALE, GENDER_FEMALE,
    REQUEST_STATUS_PENDING,
)
from app.core.exceptions import (
    NotFoundException, RideAlreadyMatchedException,
    ProfileIncompleteException, ForbiddenException,
)
from app.schemas.ping import RidePingCreate, RidePingUpdate
from app.utils.geo import create_point_wkt, extract_coordinates


class PingService:
    def __init__(self, db: Session):
        self.db = db

    def create_ping(self, user_id: uuid.UUID, data: RidePingCreate) -> RidePing:
        """Create a new ride ping."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_onboarding_complete:
            raise ProfileIncompleteException()

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=data.expires_in_minutes)
        pickup_wkt = create_point_wkt(data.pickup_lat, data.pickup_lng)

        ping = RidePing(
            id=uuid.uuid4(),
            host_id=user_id,
            pickup_geom=func.ST_GeomFromText(pickup_wkt, 4326),
            pickup_label=data.pickup_label,
            destination_label=data.destination_label,
            estimated_fare=data.estimated_fare,
            gender_preference=data.gender_preference,
            meetup_point=data.meetup_point,
            max_passengers=data.max_passengers,
            current_passengers=0,
            status=PING_STATUS_OPEN,
            expires_at=expires_at,
        )

        # Set destination geometry if provided
        if data.destination_lat and data.destination_lng:
            dest_wkt = create_point_wkt(data.destination_lat, data.destination_lng)
            ping.destination_geom = func.ST_GeomFromText(dest_wkt, 4326)

        self.db.add(ping)
        self.db.commit()
        self.db.refresh(ping)
        return ping

    def get_ping(self, ping_id: uuid.UUID) -> RidePing:
        """Get a ride ping by ID."""
        ping = self.db.query(RidePing).options(
            joinedload(RidePing.host)
        ).filter(RidePing.id == ping_id).first()
        if not ping:
            raise NotFoundException(detail="Ride ping not found")
        return ping

    def get_pings_by_host(self, host_id: uuid.UUID) -> list[RidePing]:
        """List ride pings created by a specific host."""
        query = (
            self.db.query(RidePing)
            .options(joinedload(RidePing.host))
            .filter(RidePing.host_id == host_id)
            .order_by(RidePing.created_at.desc())
        )
        return query.all()

    def get_nearby_pings(
        self,
        lat: float,
        lng: float,
        current_user_id: uuid.UUID,
        radius_meters: float = DEFAULT_SEARCH_RADIUS_METERS,
        gender_preference: str = None,
        limit: int = 20,
    ) -> list:
        """Find nearby open ride pings using PostGIS ST_DWithin.

        Filters applied:
        - status = open
        - exclude user's own rides
        - within radius
        - not blocked
        - not expired
        - capacity available (current_passengers < max_passengers)
        - gender preference compatibility
        """
        point_wkt = create_point_wkt(lat, lng)

        # Get blocked user IDs
        blocked_ids_query = self.db.query(BlockedUser.blocked_id).filter(
            BlockedUser.blocker_id == current_user_id
        )
        blocked_by_ids_query = self.db.query(BlockedUser.blocker_id).filter(
            BlockedUser.blocked_id == current_user_id
        )

        # Use GEOGRAPHY type for accurate meter-based distance calculations
        pickup_geog = cast(RidePing.pickup_geom, Geography)
        point_geog = cast(func.ST_GeomFromText(point_wkt, 4326), Geography)

        query = (
            self.db.query(
                RidePing,
                geo_func.ST_Distance(pickup_geog, point_geog).label("distance")
            )
            .options(joinedload(RidePing.host))
            .filter(
                RidePing.status == PING_STATUS_OPEN,
                RidePing.host_id != current_user_id,
                geo_func.ST_DWithin(pickup_geog, point_geog, radius_meters),
                ~RidePing.host_id.in_(blocked_ids_query),
                ~RidePing.host_id.in_(blocked_by_ids_query),
                RidePing.expires_at > datetime.now(timezone.utc),
                # Capacity filter: exclude full rides (NEW)
                RidePing.current_passengers < RidePing.max_passengers,
            )
        )

        # Apply gender preference filter
        if gender_preference == GENDER_MALE:
            query = query.filter(
                (RidePing.gender_preference == GENDER_ANY) |
                (RidePing.gender_preference == GENDER_MALE)
            )
        elif gender_preference == GENDER_FEMALE:
            query = query.filter(
                (RidePing.gender_preference == GENDER_ANY) |
                (RidePing.gender_preference == GENDER_FEMALE)
            )
        elif gender_preference and gender_preference != GENDER_ANY:
            query = query.filter(RidePing.gender_preference == gender_preference)

        # Order by distance and limit
        results = query.order_by(
            geo_func.ST_Distance(pickup_geog, point_geog)
        ).limit(limit).all()

        return results

    def find_rides(
        self,
        current_lat: float,
        current_lng: float,
        destination_lat: float,
        destination_lng: float,
        current_user_id: uuid.UUID,
        pickup_radius_meters: float = DEFAULT_FIND_PICKUP_RADIUS_METERS,
        destination_radius_meters: float = DEFAULT_FIND_DESTINATION_RADIUS_METERS,
        limit: int = 20,
    ) -> list:
        """Find rides where pickup is near user AND destination is near user's destination.

        This is the 'Find a Ride' feature — user has a specific destination in mind
        and wants rides already headed that way. The pickup radius is deliberately
        looser than the destination radius: a rider will travel further to reach a
        pickup point than they will tolerate slack on where the ride ends up.

        Filters applied:
        - status = open
        - exclude user's own rides
        - pickup within pickup_radius_meters of user's current location
        - destination within destination_radius_meters of user's desired destination
        - not blocked
        - not expired
        - capacity available
        - gender preference compatibility
        """
        pickup_wkt = create_point_wkt(current_lat, current_lng)
        dest_wkt = create_point_wkt(destination_lat, destination_lng)

        # Get blocked user IDs
        blocked_ids_query = self.db.query(BlockedUser.blocked_id).filter(
            BlockedUser.blocker_id == current_user_id
        )
        blocked_by_ids_query = self.db.query(BlockedUser.blocker_id).filter(
            BlockedUser.blocked_id == current_user_id
        )

        # Use GEOGRAPHY type for accurate meter-based distance calculations
        pickup_geog = cast(RidePing.pickup_geom, Geography)
        pickup_point_geog = cast(func.ST_GeomFromText(pickup_wkt, 4326), Geography)
        dest_geog = cast(RidePing.destination_geom, Geography)
        dest_point_geog = cast(func.ST_GeomFromText(dest_wkt, 4326), Geography)

        query = (
            self.db.query(
                RidePing,
                geo_func.ST_Distance(pickup_geog, pickup_point_geog).label("distance")
            )
            .options(joinedload(RidePing.host))
            .filter(
                RidePing.status == PING_STATUS_OPEN,
                RidePing.host_id != current_user_id,
                # Pickup must be near user's current location
                geo_func.ST_DWithin(pickup_geog, pickup_point_geog, pickup_radius_meters),
                # Destination must be near user's desired destination
                geo_func.ST_DWithin(dest_geog, dest_point_geog, destination_radius_meters),
                ~RidePing.host_id.in_(blocked_ids_query),
                ~RidePing.host_id.in_(blocked_by_ids_query),
                RidePing.expires_at > datetime.now(timezone.utc),
                RidePing.current_passengers < RidePing.max_passengers,
            )
        )

        # Apply gender preference filter using the current user's gender
        user = self.db.query(User).filter(User.id == current_user_id).first()
        user_gender = user.gender if user else GENDER_ANY

        if user_gender == GENDER_MALE:
            query = query.filter(
                (RidePing.gender_preference == GENDER_ANY) |
                (RidePing.gender_preference == GENDER_MALE)
            )
        elif user_gender == GENDER_FEMALE:
            query = query.filter(
                (RidePing.gender_preference == GENDER_ANY) |
                (RidePing.gender_preference == GENDER_FEMALE)
            )

        # Order by distance and limit
        results = query.order_by(
            geo_func.ST_Distance(pickup_geog, pickup_point_geog)
        ).limit(limit).all()

        return results

    def get_pending_requests_for_ride(self, ride_id: uuid.UUID, host_id: uuid.UUID) -> list:
        """Get all pending join requests for a ride (host only)."""
        ride = self.db.query(RidePing).filter(RidePing.id == ride_id).first()
        if not ride:
            raise NotFoundException(detail="Ride ping not found")
        if ride.host_id != host_id:
            raise ForbiddenException(detail="Only the host can view join requests")

        requests = (
            self.db.query(MatchRequest)
            .options(joinedload(MatchRequest.guest))
            .filter(
                MatchRequest.ride_id == ride_id,
                MatchRequest.status == REQUEST_STATUS_PENDING,
            )
            .order_by(MatchRequest.created_at.asc())
            .all()
        )
        return requests

    def update_ping(self, ping_id: uuid.UUID, user_id: uuid.UUID, data: RidePingUpdate) -> RidePing:
        """Update a ride ping (only host can update)."""
        ping = self.get_ping(ping_id)
        if ping.host_id != user_id:
            raise ForbiddenException(detail="Only the host can update this ride ping")
        if ping.status != PING_STATUS_OPEN:
            from app.core.exceptions import BadRequestException
            raise BadRequestException(detail="Cannot update a ride that is not open")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ping, key, value)

        self.db.commit()
        self.db.refresh(ping)
        return ping

    def cancel_ping(self, ping_id: uuid.UUID, user_id: uuid.UUID) -> RidePing:
        """Cancel a ride ping."""
        ping = self.get_ping(ping_id)
        if ping.host_id != user_id:
            raise ForbiddenException(detail="Only the host can cancel this ride ping")
        if ping.status not in (PING_STATUS_OPEN,):
            from app.core.exceptions import BadRequestException
            raise BadRequestException(detail="Cannot cancel a ride that is not open")

        ping.status = PING_STATUS_CANCELLED
        self.db.commit()
        self.db.refresh(ping)
        return ping

    def expire_ping(self, ping_id: uuid.UUID):
        """Mark a ping as expired."""
        ping = self.db.query(RidePing).filter(RidePing.id == ping_id).first()
        if ping and ping.status == PING_STATUS_OPEN:
            ping.status = PING_STATUS_EXPIRED
            self.db.commit()

    def expire_stale_pings(self):
        """Expire all pings past their expiry time."""
        now = datetime.now(timezone.utc)
        stale = (
            self.db.query(RidePing)
            .filter(
                RidePing.status == PING_STATUS_OPEN,
                RidePing.expires_at <= now,
            )
            .all()
        )
        for ping in stale:
            ping.status = PING_STATUS_EXPIRED
        self.db.commit()
        return len(stale)

    def delete_expired_pings_for_host(self, host_id: uuid.UUID) -> int:
        """Remove expired pings that belong to the given host."""
        now = datetime.now(timezone.utc)
        deleted = (
            self.db.query(RidePing)
            .filter(
                RidePing.host_id == host_id,
                RidePing.status == PING_STATUS_EXPIRED,
                RidePing.expires_at <= now,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted

    def ping_to_response(self, ping: RidePing) -> dict:
        """Convert ping model to full response dict with lat/lng."""
        lat, lng = extract_coordinates(ping.pickup_geom)
        dest_lat, dest_lng = None, None
        if ping.destination_geom:
            dest_lat, dest_lng = extract_coordinates(ping.destination_geom)

        host_data = None
        if ping.host:
            host_data = {
                "id": str(ping.host.id),
                "name": ping.host.name,
                "gender": ping.host.gender,
                "avatar_url": ping.host.avatar_url,
                "rating_avg": ping.host.rating_avg,
                "completed_rides_count": ping.host.completed_rides_count,
                "is_verified": ping.host.is_verified,
            }

        return {
            "id": str(ping.id),
            "host_id": str(ping.host_id),
            "pickup_lat": lat,
            "pickup_lng": lng,
            "pickup_label": ping.pickup_label,
            "destination_label": ping.destination_label,
            "destination_lat": dest_lat,
            "destination_lng": dest_lng,
            "estimated_fare": ping.estimated_fare,
            "final_fare": ping.final_fare,
            "gender_preference": ping.gender_preference,
            "meetup_point": ping.meetup_point,
            "max_passengers": ping.max_passengers,
            "current_passengers": ping.current_passengers or 0,
            "status": ping.status,
            "expires_at": ping.expires_at.isoformat() if ping.expires_at else None,
            "created_at": ping.created_at.isoformat() if ping.created_at else None,
            "host": host_data,
        }

    def ping_to_nearby_response(self, ping: RidePing, distance_meters: float) -> dict:
        """Convert ping model to nearby feed response dict."""
        host_data = None
        if ping.host:
            host_data = {
                "id": str(ping.host.id),
                "gender": ping.host.gender,
                "rating": ping.host.rating_avg or 0.0,
                "trust_level": "unknown",
            }

        return {
            "ride_id": str(ping.id),
            "host": host_data,
            "pickup_label": ping.pickup_label,
            "destination_label": ping.destination_label,
            "estimated_fare": ping.estimated_fare,
            "available_seats": max(
                0, (ping.max_passengers or 0) - (ping.current_passengers or 0)
            ),
            "gender_preference": ping.gender_preference,
            "distance_meters": round(distance_meters, 1),
        }
