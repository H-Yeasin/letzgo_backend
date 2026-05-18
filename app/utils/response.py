from typing import Any, Optional


def api_response(
    success: bool = True,
    message: str = "Success",
    data: Any = None,
    code: Optional[str] = None,
) -> dict:
    """Standardized API response format."""
    response = {
        "success": success,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    if code:
        response["code"] = code
    return response


def error_response(message: str, code: str = None) -> dict:
    """Standardized error response."""
    return api_response(success=False, message=message, code=code)


def success_response(data: Any = None, message: str = "Success") -> dict:
    """Standardized success response."""
    return api_response(success=True, message=message, data=data)