from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from pathlib import Path
from app.db.session import get_db
from app.core.config import UPLOAD_DIR
from app.core.security import get_current_user_id
from app.schemas.user import UserResponse, UserPublicProfile, UserUpdate
from app.services.user_service import UserService
import secrets
import uuid

router = APIRouter(prefix="/users", tags=["Users"])

# content-type -> canonical extension for avatar uploads
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
AVATAR_URL_PREFIX = "/uploads/avatars/"


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get current user's profile."""
    user_service = UserService(db)
    user = user_service.get_by_id(uuid.UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    user_service = UserService(db)
    user = user_service.update_user(uuid.UUID(user_id), data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.post("/me/avatar", response_model=UserResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Upload a profile photo. Stores the file locally and updates avatar_url."""
    ext = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if ext is None:
        # Fall back to the filename extension (some clients send octet-stream)
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only JPEG, PNG, or WebP images are allowed",
            )
        ext = ".jpg" if suffix == ".jpeg" else suffix

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be 5MB or smaller",
        )

    user_service = UserService(db)
    user = user_service.get_by_id(uuid.UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    avatars_dir = UPLOAD_DIR / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    # Random suffix busts client-side caches when re-uploading
    filename = f"{user_id}-{secrets.token_hex(4)}{ext}"
    (avatars_dir / filename).write_bytes(contents)

    # Remove the previous locally-stored avatar, if any
    old_url = user.avatar_url
    if old_url and old_url.startswith(AVATAR_URL_PREFIX):
        old_path = avatars_dir / Path(old_url).name
        try:
            old_path.unlink(missing_ok=True)
        except OSError:
            pass

    return user_service.update_user(
        uuid.UUID(user_id),
        UserUpdate(avatar_url=f"{AVATAR_URL_PREFIX}{filename}"),
    )


@router.get("/{target_id}", response_model=UserPublicProfile)
async def get_user_public_profile(
    target_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get another user's public profile (limited fields)."""
    user_service = UserService(db)
    user = user_service.get_by_id(target_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user is not available",
        )
    return user