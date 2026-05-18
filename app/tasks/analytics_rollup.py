import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import SessionLocal
from app.models.ride_ping import RidePing
from app.models.match import Match
from app.models.user import User
from app.models.report import Report

logger = logging.getLogger("uvicorn")


def compute_analytics_rollup():
    """
    Background task to compute and log analytics metrics.
    """
    db: Session = SessionLocal()
    try:
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_rides = db.query(func.count(RidePing.id)).scalar() or 0
        total_matches = db.query(func.count(Match.id)).scalar() or 0
        completed_rides = db.query(func.count(Match.id)).filter(Match.status == "completed").scalar() or 0
        cancelled_rides = db.query(func.count(Match.id)).filter(Match.status == "cancelled").scalar() or 0
        pending_reports = db.query(func.count(Report.id)).filter(Report.status == "pending").scalar() or 0

        completion_rate = round((completed_rides / total_matches * 100), 2) if total_matches > 0 else 0.0

        logger.info(
            f"Analytics Rollup — "
            f"Users: {total_users}, "
            f"Rides: {total_rides}, "
            f"Matches: {total_matches}, "
            f"Completed: {completed_rides} ({completion_rate}%), "
            f"Cancelled: {cancelled_rides}, "
            f"Pending Reports: {pending_reports}"
        )
    except Exception as e:
        logger.error(f"Analytics rollup error: {e}")
    finally:
        db.close()
