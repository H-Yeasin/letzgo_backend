import logging
from typing import Dict, List, Set
from fastapi import WebSocket
import json

logger = logging.getLogger("uvicorn")


class WebSocketManager:
    def __init__(self):
        # user_id -> set of active websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # room_name -> set of user_ids
        self.rooms: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected: user={user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected: user={user_id}")

    def join_room(self, user_id: str, room_name: str):
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
        self.rooms[room_name].add(user_id)
        logger.info(f"User {user_id} joined room {room_name}")

    def leave_room(self, user_id: str, room_name: str):
        if room_name in self.rooms:
            self.rooms[room_name].discard(user_id)
            if not self.rooms[room_name]:
                del self.rooms[room_name]
        logger.info(f"User {user_id} left room {room_name}")

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast_to_room(self, room_name: str, message: dict):
        if room_name in self.rooms:
            for user_id in list(self.rooms[room_name]):
                await self.send_to_user(user_id, message)


manager = WebSocketManager()
