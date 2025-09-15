from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class AssistantCreateRequest(BaseModel):
    model: str = Field(..., description="Model ID (e.g., gpt-4o)")
    name: Optional[str] = Field(None, max_length=256, description="Assistant name")
    description: Optional[str] = Field(
        None, max_length=512, description="Assistant description"
    )
    instructions: Optional[str] = Field(
        None, max_length=256000, description="System instructions"
    )
    tools: List[Any] = Field(
        default=[], description="Tools (function, code interpreter, file search)"
    )
    metadata: Optional[Dict[str, str]] = Field(None, description="Key-value metadata")
    temperature: Optional[float] = Field(1.0, description="Sampling temperature (0-2)")
    top_p: Optional[float] = Field(1.0, description="Nucleus sampling value (0-1)")
    response_format: Optional[str] = Field(
        "auto", description="Response format (json, text, auto)"
    )
