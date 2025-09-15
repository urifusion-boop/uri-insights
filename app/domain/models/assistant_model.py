from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class tool(BaseModel):
    type: str = "function"
    function: Dict[str, Any]


class CodeInterpreterTool(BaseModel):
    type: str = "code_interpreter"


class FileSearchTool(BaseModel):
    type: str = "file_search"
    file_search: Optional[Dict[str, Any]] = None


class AssistantModel(BaseModel):
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
