from pydantic import BaseModel
from typing import List
from app.domain.models.chat_model import ChatMessage


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class EmbeddingRequest(BaseModel):
    input: str


class ImageRequest(BaseModel):
    prompt: str
    n: int = 1
    size: str = "1024x1024"


class AudioRequest(BaseModel):
    url: str
