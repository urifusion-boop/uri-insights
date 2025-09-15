from typing import List, Optional
from pydantic import BaseModel


class PostModel(BaseModel):
    username: str
    comment: str
    like_count: int
    timestamp: str
    profile_link: str
    source: Optional[str] = "Nairaland"


class ExtractModel(BaseModel):
    posts: List[PostModel]
