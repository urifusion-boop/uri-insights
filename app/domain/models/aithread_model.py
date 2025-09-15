from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from bson import ObjectId


class TextContent(BaseModel):
    type: str = Field("text", description="Always 'text'.")
    text: str = Field(..., description="Text content of the message.")


class ImageFileContent(BaseModel):
    type: str = Field("image_file", description="Always 'image_file'.")
    image_file: Dict[str, str] = Field(
        ..., description="File reference for an uploaded image."
    )


class ImageUrlContent(BaseModel):
    type: str = Field("image_url", description="Always 'image_url'.")
    image_url: Dict[str, Any] = Field(..., description="External image URL reference.")


class MessageAttachment(BaseModel):
    file_id: str = Field(
        ..., description="The ID of the file to attach to the message."
    )
    tools: Optional[List[Dict[str, str]]] = Field(
        None, description="List of tools the file should be added to."
    )


class AiThreadMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: List[Dict[str, Any]] = Field(
        ..., description="Message content (text, images, attachments, etc.)."
    )
    attachments: Optional[List[MessageAttachment]] = Field(
        None, description="A list of files attached to the message."
    )


class ToolResources(BaseModel):
    code_interpreter: Optional[Dict[str, List[str]]] = Field(
        None, description="File IDs available to the code interpreter tool."
    )
    file_search: Optional[Dict[str, List[str]]] = Field(
        None, description="Vector store IDs available for file search."
    )


class AiThreadModel(BaseModel):
    id: str = Field(
        default_factory=lambda: str(ObjectId()), description="MongoDB ObjectId"
    )
    thread_id: str = Field(..., description="Thread ID from OpenAI API")
    thread_type: str
    run_id: Optional[str] = Field(
        None, description="The ID of the latest run associated with this thread"
    )
    assistant_id: Optional[str] = Field(
        None, description="The assistant assigned to this thread"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Date the thread was created"
    )
    metadata: Optional[Dict[str, str]] = None
    tool_resources: Optional[Any] = None
    messages: List[Dict[str, Any]] = Field(
        ..., description="List of messages in the thread"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
