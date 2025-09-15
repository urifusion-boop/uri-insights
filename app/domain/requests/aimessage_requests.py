from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class AiMessageCreateRequest(BaseModel):
    role: str = Field(..., description="Who is sending the message (user/assistant)")
    content: List[Dict[str, Any]] = Field(
        ..., description="Message content (text, images, etc.)"
    )
    attachments: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, str]] = None


class AiMessageUpdateRequest(BaseModel):
    metadata: Optional[Dict[str, str]] = None
