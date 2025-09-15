from datetime import datetime
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from app.domain.models.aithread_model import AiThreadModel


class AiRunResponse(BaseModel):
    run_id: str
    object: str = "thread.run"
    created_at: datetime
    thread_id: str
    assistant_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    model: Optional[str] = None
    instructions: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_resources: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, str]] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    max_prompt_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    truncation_strategy: Optional[Dict[str, Any]] = None
    response_format: Optional[str] = None
    tool_choice: Optional[str] = None
    parallel_tool_calls: Optional[bool] = True
    usage: Optional[Dict[str, int]] = None
