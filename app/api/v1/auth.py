import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import OTPRequest, OTPVerify, AuthResponse, UserCreate, UserUpdate
from app.schemas.admin import AdminLoginRequest, AdminLoginResponse
from app.services.user_service import UserService, normalize_bd_phone
from app.core.security import create_access_token, verify_password

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/send-otp", status_code=status.HTTP_200_OK)
async def send_otp(data: OTPRequest, db: Session = Depends(get_db)):
    """
    Send OTP to phone number.
    In MVP, we accept any 6-digit OTP (123456 for dev).
    Production would integrate with a real SMS gateway.
    """
    # In development, always succeed
    # In production, integrate with SMS gateway (e.g., Twilio, BKash, etc.)
    logger.info(f"OTP sent to {data.phone}: 123456")
    return {
        "success": True,
        "message": "OTP sent successfully",
        "phone": data.phone,
        "debug_otp": "123456",  # Remove in production
    }


@router.post("/admin-login", response_model=AdminLoginResponse)
async def admin_login(data: AdminLoginRequest, db: Session = Depends(get_db)):
    """
    Admin login endpoint.
    Verifies phone number + password and returns JWT token.
    Only users with is_admin=True and a password set can login here.
    """
    user_service = UserService(db)
    user = user_service.get_by_phone(normalize_bd_phone(data.phone))

    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password",
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked",
        )

    access_token = create_access_token(data={"sub": str(user.id), "is_admin": True})
    return AdminLoginResponse(access_token=access_token)


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(data: OTPVerify, db: Session = Depends(get_db)):
    """
    Verify OTP and authenticate user.
    On first login, creates a new user account.
    """
    # MVP: Accept any 6-digit OTP
    # Production: Verify against SMS gateway
    if len(data.otp) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP",
        )

    user_service = UserService(db)
    user = user_service.get_by_phone(data.phone)

    if user:
        return user_service.generate_auth_response(user, is_new_user=False)
    else:
        # Create new user
        new_user = user_service.create_user(UserCreate(phone=data.phone))
        return user_service.generate_auth_response(new_user, is_new_user=True)


@router.post("/register", response_model=AuthResponse)
async def complete_registration(
    data: UserCreate, db: Session = Depends(get_db)
):
    """Complete user profile after initial OTP verification."""
    user_service = UserService(db)

    # Check if phone already exists
    existing = user_service.get_by_phone(data.phone)
    if existing:
        # If user exists but hasn't completed onboarding, update them
        # Otherwise, if they are already fully registered, then it's a conflict
        if not existing.is_onboarding_complete:
            updated_user = user_service.update_user(
                existing.id, 
                UserUpdate(
                    name=data.name,
                    gender=data.gender,
                    avatar_url=data.avatar_url,
                    fcm_token=data.fcm_token,
                    is_onboarding_complete=True
                )
            )
            return user_service.generate_auth_response(updated_user, is_new_user=False)
        
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already fully registered",
        )

    # If user doesn't exist, create them as fully onboarded
    user = user_service.create_user(data)
    # Ensure onboarding is marked complete if created through this endpoint
    if not user.is_onboarding_complete:
        user = user_service.update_user(user.id, UserUpdate(is_onboarding_complete=True))
    
    return user_service.generate_auth_response(user, is_new_user=True)