from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.db.session import get_db
from app.core.security import get_current_user_id
from app.models.user import User
from app.models.ride_ping import RidePing
from app.models.match import Match
from app.models.match_request import MatchRequest
from app.models.report import Report
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminRideListResponse,
    AdminRideResponse,
    AdminReportListResponse,
    AdminReportResponse,
    AdminUpdateReportStatus,
    AdminDisputeListResponse,
    AdminDisputeResponse,
    AdminUpdateDisputeStatus,
    AdminMeetupReportListResponse,
    AdminMeetupReportResponse,
    BlockUnblockResponse,
    CancellationStats,
)
import uuid
from typing import Optional

router = APIRouter(prefix="/admin", tags=["Admin"])


def verify_admin(user_id: str, db: Session):
    """Ensure the current user is an admin."""
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ─── Dashboard Stats ───────────────────────────────────────────────────────────


@router.get("/stats", response_model=AdminStatsResponse)
async def get_dashboard_stats(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get overall admin dashboard statistics."""
    verify_admin(user_id, db)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_rides = (
        db.query(func.count(RidePing.id))
        .filter(RidePing.status.in_(["open", "matched"]))
        .scalar()
        or 0
    )
    completed_rides = (
        db.query(func.count(Match.id))
        .filter(Match.status == "completed")
        .scalar()
        or 0
    )
    pending_reports = (
        db.query(func.count(Report.id))
        .filter(Report.status == "pending")
        .scalar()
        or 0
    )
    open_disputes = (
        db.query(func.count(Match.id))
        .filter(Match.status == "disputed")
        .scalar()
        or 0
    )

    total_rides_created = db.query(func.count(RidePing.id)).scalar() or 1
    total_cancelled = (
        db.query(func.count(RidePing.id))
        .filter(RidePing.status == "cancelled")
        .scalar()
        or 0
    )
    cancellation_rate = round((total_cancelled / total_rides_created) * 100, 2)

    return AdminStatsResponse(
        total_users=total_users,
        active_rides=active_rides,
        completed_rides=completed_rides,
        pending_reports=pending_reports,
        open_disputes=open_disputes,
        cancellation_rate=cancellation_rate,
    )


@router.get("/stats/cancellations", response_model=CancellationStats)
async def get_cancellation_stats(
    days: Optional[int] = Query(7, description="Number of days to analyze"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get ride cancellation rate statistics."""
    verify_admin(user_id, db)

    total_rides_created = db.query(func.count(RidePing.id)).scalar() or 1
    total_cancelled = (
        db.query(func.count(RidePing.id))
        .filter(RidePing.status == "cancelled")
        .scalar()
        or 0
    )
    cancellation_rate = round((total_cancelled / total_rides_created) * 100, 2)

    return CancellationStats(
        total_rides_created=total_rides_created,
        total_cancelled=total_cancelled,
        cancellation_rate=cancellation_rate,
        daily_breakdown={"period_days": days},
    )


# ─── User Management ───────────────────────────────────────────────────────────


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name or phone"),
    is_blocked: Optional[bool] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List all users with optional filtering."""
    verify_admin(user_id, db)

    query = db.query(User)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_term)) | (User.phone.ilike(search_term))
        )
    if is_blocked is not None:
        query = query.filter(User.is_blocked == is_blocked)

    total = query.count()
    offset = (page - 1) * per_page
    users = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()

    return AdminUserListResponse(
        total=total,
        users=[AdminUserResponse.model_validate(u) for u in users],
    )


@router.get("/users/{target_id}", response_model=AdminUserResponse)
async def get_user_detail(
    target_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get detailed info about a specific user."""
    verify_admin(user_id, db)

    user = db.query(User).filter(User.id == target_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{target_id}/block", response_model=BlockUnblockResponse)
async def block_user(
    target_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Block a user."""
    verify_admin(user_id, db)

    user = db.query(User).filter(User.id == target_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot block an admin user")

    user.is_blocked = True
    db.commit()
    db.refresh(user)

    return BlockUnblockResponse(
        user_id=user.id,
        is_blocked=True,
        message=f"User {user.name} has been blocked",
    )


@router.patch("/users/{target_id}/unblock", response_model=BlockUnblockResponse)
async def unblock_user(
    target_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Unblock a user."""
    verify_admin(user_id, db)

    user = db.query(User).filter(User.id == target_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_blocked = False
    db.commit()
    db.refresh(user)

    return BlockUnblockResponse(
        user_id=user.id,
        is_blocked=False,
        message=f"User {user.name} has been unblocked",
    )


# ─── Ride Management ───────────────────────────────────────────────────────────


@router.get("/rides/active", response_model=AdminRideListResponse)
async def list_active_rides(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List all active (matched/in_progress) rides."""
    verify_admin(user_id, db)

    query = (
        db.query(RidePing)
        .filter(RidePing.status.in_(["matched", "open"]))
        .order_by(RidePing.created_at.desc())
    )

    total = query.count()
    offset = (page - 1) * per_page
    rides = query.offset(offset).limit(per_page).all()

    ride_responses = []
    for ride in rides:
        host = db.query(User).filter(User.id == ride.host_id).first()
        guest_count = (
            db.query(func.count(Match.id))
            .filter(
                Match.ride_id == ride.id,
                Match.status.in_(["matched", "in_progress", "completed"]),
            )
            .scalar()
            or 0
        )
        cancelled_count = (
            db.query(func.count(Match.id))
            .filter(Match.ride_id == ride.id, Match.status == "cancelled")
            .scalar()
            or 0
        )

        ride_responses.append(
            AdminRideResponse(
                id=ride.id,
                host_id=ride.host_id,
                host_name=host.name if host else None,
                pickup_label=ride.pickup_label,
                destination_label=ride.destination_label,
                estimated_fare=ride.estimated_fare,
                final_fare=ride.final_fare,
                status=ride.status,
                gender_preference=ride.gender_preference,
                max_passengers=ride.max_passengers,
                current_passengers=ride.current_passengers or 0,
                created_at=ride.created_at,
                expires_at=ride.expires_at,
                guest_count=guest_count,
                cancelled_count=cancelled_count,
            )
        )

    return AdminRideListResponse(total=total, rides=ride_responses)


@router.get("/rides/completed", response_model=AdminRideListResponse)
async def list_completed_rides(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List all completed rides."""
    verify_admin(user_id, db)

    completed_ride_ids = (
        db.query(Match.ride_id)
        .filter(Match.status == "completed")
        .distinct()
        .subquery()
    )
    query = db.query(RidePing).filter(RidePing.id.in_(completed_ride_ids))

    total = query.count()
    offset = (page - 1) * per_page
    rides = query.order_by(RidePing.created_at.desc()).offset(offset).limit(per_page).all()

    ride_responses = []
    for ride in rides:
        host = db.query(User).filter(User.id == ride.host_id).first()
        guest_count = (
            db.query(func.count(Match.id))
            .filter(Match.ride_id == ride.id, Match.status == "completed")
            .scalar()
            or 0
        )

        ride_responses.append(
            AdminRideResponse(
                id=ride.id,
                host_id=ride.host_id,
                host_name=host.name if host else None,
                pickup_label=ride.pickup_label,
                destination_label=ride.destination_label,
                estimated_fare=ride.estimated_fare,
                final_fare=ride.final_fare,
                status=ride.status,
                gender_preference=ride.gender_preference,
                max_passengers=ride.max_passengers,
                current_passengers=ride.current_passengers or 0,
                created_at=ride.created_at,
                expires_at=ride.expires_at,
                guest_count=guest_count,
                cancelled_count=0,
            )
        )

    return AdminRideListResponse(total=total, rides=ride_responses)


# ─── Reports & Meetup Reports ──────────────────────────────────────────────────


@router.get("/reports", response_model=AdminReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List all user reports (excluding unsafe_meetup reason)."""
    verify_admin(user_id, db)

    query = db.query(Report).filter(Report.reason != "unsafe_meetup")
    if status_filter:
        query = query.filter(Report.status == status_filter)

    total = query.count()
    offset = (page - 1) * per_page
    reports = query.order_by(Report.created_at.desc()).offset(offset).limit(per_page).all()

    report_responses = []
    for r in reports:
        reporter = db.query(User).filter(User.id == r.reporter_id).first()
        reported_user = db.query(User).filter(User.id == r.reported_user_id).first()

        report_responses.append(
            AdminReportResponse(
                id=r.id,
                reporter_id=r.reporter_id,
                reporter_name=reporter.name if reporter else None,
                reported_user_id=r.reported_user_id,
                reported_user_name=reported_user.name if reported_user else None,
                match_id=r.match_id,
                reason=r.reason,
                description=r.description,
                status=r.status,
                created_at=r.created_at,
            )
        )

    return AdminReportListResponse(total=total, reports=report_responses)


@router.patch("/reports/{report_id}", response_model=AdminReportResponse)
async def update_report_status(
    report_id: uuid.UUID,
    data: AdminUpdateReportStatus,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update report status (reviewed, resolved, dismissed)."""
    verify_admin(user_id, db)

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = data.status
    db.commit()
    db.refresh(report)

    reporter = db.query(User).filter(User.id == report.reporter_id).first()
    reported_user = db.query(User).filter(User.id == report.reported_user_id).first()

    return AdminReportResponse(
        id=report.id,
        reporter_id=report.reporter_id,
        reporter_name=reporter.name if reporter else None,
        reported_user_id=report.reported_user_id,
        reported_user_name=reported_user.name if reported_user else None,
        match_id=report.match_id,
        reason=report.reason,
        description=report.description,
        status=report.status,
        created_at=report.created_at,
    )


@router.get("/meetup-reports", response_model=AdminMeetupReportListResponse)
async def list_unsafe_meetup_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List unsafe meetup point reports."""
    verify_admin(user_id, db)

    query = db.query(Report).filter(Report.reason == "unsafe_meetup")
    if status_filter:
        query = query.filter(Report.status == status_filter)

    total = query.count()
    offset = (page - 1) * per_page
    reports = query.order_by(Report.created_at.desc()).offset(offset).limit(per_page).all()

    report_responses = []
    for r in reports:
        reporter = db.query(User).filter(User.id == r.reporter_id).first()
        reported_user = db.query(User).filter(User.id == r.reported_user_id).first()

        report_responses.append(
            AdminMeetupReportResponse(
                id=r.id,
                reporter_id=r.reporter_id,
                reporter_name=reporter.name if reporter else None,
                reported_user_id=r.reported_user_id,
                reported_user_name=reported_user.name if reported_user else None,
                match_id=r.match_id,
                description=r.description,
                status=r.status,
                created_at=r.created_at,
            )
        )

    return AdminMeetupReportListResponse(total=total, reports=report_responses)


# ─── Disputes ──────────────────────────────────────────────────────────────────


@router.get("/disputes", response_model=AdminDisputeListResponse)
async def list_disputes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List all disputed rides."""
    verify_admin(user_id, db)

    query = db.query(Match).filter(Match.status == "disputed")

    total = query.count()
    offset = (page - 1) * per_page
    disputes = query.order_by(Match.created_at.desc()).offset(offset).limit(per_page).all()

    dispute_responses = []
    for d in disputes:
        host = db.query(User).filter(User.id == d.host_id).first()
        guest = db.query(User).filter(User.id == d.guest_id).first()

        dispute_responses.append(
            AdminDisputeResponse(
                id=d.id,
                ride_id=d.ride_id,
                host_id=d.host_id,
                host_name=host.name if host else None,
                guest_id=d.guest_id,
                guest_name=guest.name if guest else None,
                status=d.status,
                started_at=d.started_at,
                completed_at=d.completed_at,
                created_at=d.created_at,
            )
        )

    return AdminDisputeListResponse(total=total, disputes=dispute_responses)


@router.patch("/disputes/{dispute_id}", response_model=AdminDisputeResponse)
async def resolve_dispute(
    dispute_id: uuid.UUID,
    data: AdminUpdateDisputeStatus,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Resolve or dismiss a dispute."""
    verify_admin(user_id, db)

    dispute = db.query(Match).filter(Match.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.status != "disputed":
        raise HTTPException(status_code=400, detail="This match is not in disputed status")

    dispute.status = data.status
    db.commit()
    db.refresh(dispute)

    host = db.query(User).filter(User.id == dispute.host_id).first()
    guest = db.query(User).filter(User.id == dispute.guest_id).first()

    return AdminDisputeResponse(
        id=dispute.id,
        ride_id=dispute.ride_id,
        host_id=dispute.host_id,
        host_name=host.name if host else None,
        guest_id=dispute.guest_id,
        guest_name=guest.name if guest else None,
        status=dispute.status,
        started_at=dispute.started_at,
        completed_at=dispute.completed_at,
        created_at=dispute.created_at,
    )