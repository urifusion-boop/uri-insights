from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from app.domain.models.aithread_model import AiThreadModel


class AiThreadsListResponse(BaseModel):
    object: str
    data: List[AiThreadModel]
    first_id: Optional[str]
    last_id: Optional[str]
    has_more: bool
