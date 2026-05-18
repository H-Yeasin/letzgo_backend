import logging
from app.db.session import SessionLocal
from app.services.ping_service import PingService

logger = logging.getLogger("uvicorn")


def expire_stale_pings():
    """Background task to expire pings past their expiry time."""
    db = SessionLocal()
    try:
        service = PingService(db)
        count = service.expire_stale_pings()
        if count > 0:
            logger.info(f"Expired {count} stale pings")
    except Exception as e:
        logger.error(f"Error in expire_stale_pings: {e}")
    finally:
        db.close()


def cleanup_old_chat_messages():
    pass


def cleanup_stale_matches():
    pass


def compute_analytics_rollup():
    pass
