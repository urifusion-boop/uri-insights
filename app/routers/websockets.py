# import json
# from typing import Any
# from fastapi import APIRouter, WebSocket
# from app.core.managers.WebsocketConnectionManager import WebSocketConnectionManager
# from app.domain.responses.uri_response import UriResponse

# router = APIRouter()

# manager = WebSocketConnectionManager.get_instance()


# @router.websocket("/connect")
# async def websocket_endpoint(websocket: WebSocket):
#     await manager.connect(websocket)
#     try:
#         while True:
#             data = await websocket.receive_text()
#             await manager.broadcast(f"You said: {data}")
#     except Exception as e:
#         print("WebSocket error:", e)
#     finally:
#         manager.disconnect(websocket)


# @router.post("/test-message")
# async def test_message(message: dict):
#     try:
#         message_to_send = json.dumps(message)
#         await manager.broadcast(message_to_send)
#         return {"message": "Testing in progress..."}
#     except Exception as e:
#         print("WebSocket error:", e)
#         return {"message": "Testing failed..."}
