import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.db.session import get_db
from app.core.security import get_current_user_id

# API routers
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.admin import router as admin_router
from app.api.v1.pings import router as pings_router
from app.api.v1.rides import router as rides_router
from app.api.v1.matches import router as matches_router
from app.api.v1.chat import router as chat_router
from app.api.v1.ratings import router as ratings_router
from app.api.v1.reports import router as reports_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.fare import router as fare_router
from app.api.v1.geocode import router as geocode_router

# WebSocket handlers
from app.websocket.handlers.chat_handler import handle_chat_websocket
from app.websocket.handlers.match_handler import handle_match_websocket
from app.websocket.handlers.notification_handler import handle_notification_websocket

# Background tasks
from app.tasks.expire_pings import expire_stale_pings
from app.tasks.cleanup_chat import cleanup_old_chat_messages
from app.tasks.cleanup_matches import cleanup_stale_matches
from app.tasks.analytics_rollup import compute_analytics_rollup

logger = logging.getLogger("uvicorn")

# ─── Rate Limiter ────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── Background Scheduler ────────────────────────────────────────────────────────
scheduler = BackgroundScheduler()


def init_scheduler():
    """Initialize background scheduled tasks."""
    scheduler.add_job(
        expire_stale_pings,
        "interval",
        minutes=1,
        id="expire_pings",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_old_chat_messages,
        "interval",
        hours=6,
        id="cleanup_chat",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_stale_matches,
        "interval",
        hours=1,
        id="cleanup_matches",
        replace_existing=True,
    )
    scheduler.add_job(
        compute_analytics_rollup,
        "interval",
        hours=24,
        id="analytics_rollup",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background scheduler started with jobs: expire_pings, cleanup_chat, cleanup_matches, analytics_rollup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    init_scheduler()
    yield
    # Shutdown
    scheduler.shutdown(wait=False)


# ─── FastAPI App ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(pings_router, prefix="/api/v1")
app.include_router(rides_router, prefix="/api/v1")
app.include_router(matches_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(ratings_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(fare_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(geocode_router, prefix="/api/v1")

# ─── WebSocket Endpoints ─────────────────────────────────────────────────────────


@app.websocket("/ws/chat/{match_id}")
async def websocket_chat(websocket: WebSocket, match_id: str, db: Session = Depends(get_db)):
    await handle_chat_websocket(websocket, match_id, db)


@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    await handle_notification_websocket(websocket)


@app.websocket("/ws/matches")
async def websocket_matches(websocket: WebSocket, db: Session = Depends(get_db)):
    await handle_match_websocket(websocket, db)


# ─── Health & Root Endpoints ─────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)