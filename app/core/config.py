from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path
import os

# Repository root of the backend (letzgo_backend/)
BASE_DIR = Path(__file__).resolve().parents[2]
# Local storage for user-uploaded files, served at /uploads
UPLOAD_DIR = BASE_DIR / "uploads"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "LetzGo"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/letzgo_db"

    # JWT
    JWT_SECRET: str = "your-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 72

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-credentials.json"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()