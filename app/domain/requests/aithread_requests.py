from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.domain.models.aithread_model import AiThreadMessage, ToolResources


class AiThreadCreateRequest(BaseModel):
    messages: Optional[List[AiThreadMessage]] = Field(
        [], description="List of messages to start the thread with."
    )
    metadata: Optional[Dict[str, str]] = Field(
        None, description="Optional metadata for the thread."
    )
    tool_resources: Optional[ToolResources] = Field(
        None, description="Resources available to the assistant's tools in this thread."
    )


class AiThreadUpdateRequest(BaseModel):
    metadata: Optional[Dict[str, str]] = None
    tool_resources: Optional[ToolResources] = None
