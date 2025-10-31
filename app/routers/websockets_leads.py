from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.services.LeadNotificationManager import LeadNotificationManager
from app.core.auth_handler import AuthHandler
from typing import Optional

router = APIRouter()
notification_manager = LeadNotificationManager()

@router.websocket("/ws/leads/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = None
):
    """WebSocket endpoint for real-time lead notifications."""
    try:
        # Verify the user's token
        if not token or not await AuthHandler.verify_access_token(token):
            await websocket.close(code=4001, reason="Unauthorized")
            return
            
        # Connect the WebSocket
        await notification_manager.manager.connect(websocket, user_id)
        
        try:
            # Keep the connection alive and handle incoming messages
            while True:
                data = await websocket.receive_json()
                # Handle any client-side messages if needed
                print(f"Received message from user {user_id}: {data}")
                
        except WebSocketDisconnect:
            # Clean up on disconnect
            await notification_manager.manager.disconnect(websocket, user_id)
            
    except Exception as e:
        print(f"Error in websocket connection: {e}")
        await websocket.close(code=4000, reason="Internal server error")