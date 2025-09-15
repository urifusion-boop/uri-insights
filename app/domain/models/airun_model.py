from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from bson import ObjectId


class AiRunModel(BaseModel):
    id: str = Field(
        default_factory=lambda: str(ObjectId()), description="MongoDB ObjectId"
    )
    run_id: str = Field(..., description="Unique ID for the run from OpenAI API")
    thread_id: str = Field(..., description="Thread ID associated with this run")
    assistant_id: str = Field(..., description="The assistant executing this run")
    status: str = Field(
        ..., description="Status of the run (queued, in_progress, completed, etc.)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Run creation timestamp"
    )
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

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
