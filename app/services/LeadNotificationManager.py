from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import asyncio
from app.core.config import settings


class ConnectionManager:
    """Manage WebSocket connections for real-time notifications."""
    
    def __init__(self):
        # Store active connections: {user_id: List[WebSocket]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket for a user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket for a user."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user's connections."""
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    dead_connections.append(connection)
                    
            # Clean up dead connections
            for dead_conn in dead_connections:
                await self.disconnect(dead_conn, user_id)
                
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users."""
        for user_id in self.active_connections:
            await self.send_personal_message(message, user_id)


class LeadNotificationManager:
    """Handle real-time lead notifications via WebSocket."""
    
    def __init__(self):
        self.manager = ConnectionManager()
        
    async def handle_new_lead(self, lead: dict):
        """Process and send a new lead notification."""
        user_id = lead.get("user_id")
        if not user_id:
            return
            
        notification = {
            "type": "new_lead",
            "timestamp": DateHelper.utc_now_iso(),
            "data": {
                "lead_id": lead.get("lead_id"),
                "source": lead.get("source"),
                "matched_keywords": lead.get("source", {}).get("matched_keywords", []),
                "matched_signals": lead.get("source", {}).get("matched_signals", []),
                "ai_suggested_reply": lead.get("ai_suggested_reply")
            }
        }
        
        await self.manager.send_personal_message(notification, user_id)
        
    async def handle_lead_update(self, lead_id: str, update: dict, user_id: str):
        """Send a lead update notification."""
        notification = {
            "type": "lead_update",
            "timestamp": DateHelper.utc_now_iso(),
            "data": {
                "lead_id": lead_id,
                "updates": update
            }
        }
        
        await self.manager.send_personal_message(notification, user_id)
        
    async def handle_monitoring_status(self, user_id: str, status: dict):
        """Send monitoring status updates."""
        notification = {
            "type": "monitoring_status",
            "timestamp": DateHelper.utc_now_iso(),
            "data": status
        }
        
        await self.manager.send_personal_message(notification, user_id)