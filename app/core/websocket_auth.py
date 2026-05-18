import uuid
from typing import Optional, Tuple
from jose import jwt, JWTError
from app.core.config import settings


async def verify_websocket_token(token: str) -> Optional[Tuple[uuid.UUID, str]]:
    """Verify JWT token for WebSocket connections."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        return uuid.UUID(user_id_str), user_id_str
    except (JWTError, ValueError):
        return None