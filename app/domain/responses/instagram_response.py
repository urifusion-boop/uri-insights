from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class InsightResponse(BaseModel):
    name: str
    period: str
    values: List[dict]
    title: str
    description: str
    id: str
