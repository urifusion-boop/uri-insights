from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class AiRunCreateRequest(BaseModel):
    assistant_id: str = Field(..., description="The assistant executing this run")
    model: Optional[str] = None
    instructions: Optional[str] = None
    additional_instructions: Optional[str] = None
    additional_messages: Optional[List[Dict[str, Any]]] = None
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


class AiRunUpdateRequest(BaseModel):
    metadata: Optional[Dict[str, str]] = Field(
        None, description="Key-value metadata updates"
    )
    function_response: Optional[dict] = Field(
        None, description="Response from a function execution"
    )
