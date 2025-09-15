# import asyncio
# from fastapi import WebSocket
# from typing import Dict, List, Optional

# import websockets


# class WebSocketConnectionManager:
#     _instance: Optional["WebSocketConnectionManager"] = None

#     def __init__(self):
#         if WebSocketConnectionManager._instance is not None:
#             raise Exception("This class is a singleton!")
#         self.active_connections: List[WebSocket] = []
#         WebSocketConnectionManager._instance = self

#     @classmethod
#     def get_instance(cls) -> "WebSocketConnectionManager":
#         if cls._instance is None:
#             cls._instance = cls()
#         return cls._instance

#     async def connect(self, websocket: WebSocket):
#         await websocket.accept()
#         self.active_connections.append(websocket)

#     def disconnect(self, websocket: WebSocket):
#         if websocket in self.active_connections:
#             self.active_connections.remove(websocket)

#     async def broadcast(self, message: str):
#         disconnected = []
#         for connection in self.active_connections:
#             try:
#                 await asyncio.wait_for(connection.send_text(message), timeout=5)
#             except websockets.ConnectionClosed:
#                 disconnected.append(connection)
#             except Exception as e:
#                 print("Exception occurred in ws messaging: ", e)
#                 disconnected.append(connection)

#         for conn in disconnected:
#             self.active_connections.remove(conn)
