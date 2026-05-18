from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception with error code."""

    def __init__(self, status_code: int, detail: str, code: str = None):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code or detail.upper().replace(" ", "_")


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, code=code)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Unauthorized", code: str = "UNAUTHORIZED"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, code=code)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Forbidden", code: str = "FORBIDDEN"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, code=code)


class ConflictException(AppException):
    def __init__(self, detail: str = "Conflict", code: str = "CONFLICT"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, code=code)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad request", code: str = "BAD_REQUEST"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, code=code)


class RideAlreadyMatchedException(ConflictException):
    def __init__(self):
        super().__init__(detail="Ride already matched", code="RIDE_MATCHED")


class RideExpiredException(BadRequestException):
    def __init__(self):
        super().__init__(detail="Ride has expired", code="RIDE_EXPIRED")


class ProfileIncompleteException(ForbiddenException):
    def __init__(self):
        super().__init__(detail="Complete your profile to perform this action", code="PROFILE_INCOMPLETE")


class UserBlockedException(ForbiddenException):
    def __init__(self):
        super().__init__(detail="You cannot interact with this user", code="USER_BLOCKED")


class InvalidStateTransitionException(BadRequestException):
    def __init__(self, current: str, target: str):
        super().__init__(
            detail=f"Cannot transition from '{current}' to '{target}'",
            code="INVALID_STATE_TRANSITION",
        )