from typing import Optional
from pydantic import BaseModel

from app.domain.enums.wsmessagetype_enum import WsMessageTypeEnum


class Message(BaseModel):
    user_id: str
    data: Optional[dict] = None


class WsRequest(BaseModel):
    message_type: WsMessageTypeEnum
    message: Message
