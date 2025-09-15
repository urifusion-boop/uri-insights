from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatResponseUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatChoice(BaseModel):
    message: ChatMessage
    finish_reason: Optional[str] = None
    index: Optional[int] = None
    logprobs: Optional[Any] = None


class ChatUsage(BaseModel):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    usage: ChatUsage
    choices: List[ChatChoice]


class EmbeddingResponse(BaseModel):
    data: List[Dict]


class ImageResponse(BaseModel):
    data: List[Dict]


class AudioResponse(BaseModel):
    url: str
