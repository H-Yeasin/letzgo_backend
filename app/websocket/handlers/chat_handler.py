import logging
from fastapi import WebSocket, Depends
from app.services.websocket_manager import manager
from app.core.websocket_auth import verify_websocket_token

logger = logging.getLogger("uvicorn")


async def handle_chat_websocket(websocket: WebSocket, match_id: str, db):
    """Handle chat WebSocket connections."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    # In a real app, verify token and check match participation
    # result = await verify_websocket_token(token)
    user_id = "temp_user_id" # Placeholder logic for MVP
    
    room = f"chat:{match_id}"
    await manager.connect(websocket, user_id)
    manager.join_room(user_id, room)
    
    try:
        while True:
            data = await websocket.receive_json()
            # Broadcast message to room
            await manager.broadcast_to_room(room, {
                "user_id": user_id,
                "message": data.get("message"),
                "type": "chat_message"
            })
    except Exception as e:
        logger.error(f"Chat WS error: {e}")
    finally:
        manager.leave_room(user_id, room)
        manager.disconnect(websocket, user_id)


async def handle_notification_websocket(websocket: WebSocket):
    """Handle notification WebSocket connections."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
        
    user_id = "temp_user_id"
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            await websocket.receive_text() # Keep alive
    except:
        pass
    finally:
        manager.disconnect(websocket, user_id)


async def handle_match_websocket(websocket: WebSocket, db):
    """Handle match status update WebSocket connections."""
    # Similar logic for match status updates
    pass
