from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from bson import ObjectId


class TextContent(BaseModel):
    type: str = Field("text", description="Always 'text'.")
    text: Dict[str, Any] = Field(..., description="Text content with annotations.")


class ImageFileContent(BaseModel):
    type: str = Field("image_file", description="Always 'image_file'.")
    image_file: Dict[str, str] = Field(..., description="File reference for an image.")


class ImageUrlContent(BaseModel):
    type: str = Field("image_url", description="Always 'image_url'.")
    image_url: Dict[str, Any] = Field(..., description="External image URL reference.")


class MessageAttachment(BaseModel):
    file_id: str = Field(..., description="The ID of the file to attach.")
    tools: Optional[List[Dict[str, str]]] = Field(
        None, description="List of tools for the file."
    )


class AiMessageModel(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    message_id: str = Field(..., description="Message ID from OpenAI API")
    thread_id: str = Field(..., description="Thread ID this message belongs to")
    assistant_id: Optional[str] = Field(
        None, description="The assistant that generated this message"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    role: str = Field(..., description="Who sent the message (user or assistant)")
    content: List[Dict[str, Any]] = Field(
        ..., description="Message content (text, images, etc.)."
    )
    run_id: Optional[str] = None
    attachments: Optional[List[MessageAttachment]] = None
    metadata: Optional[Dict[str, str]] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        populate_by_name = True
