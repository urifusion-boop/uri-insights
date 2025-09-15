from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class AssistantResponse(BaseModel):
    id: str
    object: str
    created_at: int
    name: Optional[str]
    description: Optional[str]
    model: str
    instructions: Optional[str]
    tools: List[Any]
    metadata: Optional[Dict[str, str]]
    top_p: float
    temperature: float
    response_format: str


class AssistantsListResponse(BaseModel):
    object: str
    data: List[AssistantResponse]
    first_id: Optional[str]
    last_id: Optional[str]
    has_more: bool
