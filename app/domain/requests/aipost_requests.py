from typing import List, Optional

from pydantic import BaseModel

from app.domain.enums.aiposttype_enum import PostTypeEnum


class AIPostStructure(BaseModel):
    media_type: Optional[PostTypeEnum] = None
    content: Optional[str] = None
    engagement_count: Optional[int] = None
    share_count: Optional[int] = None
    comment_count: Optional[int] = None
    post_time: Optional[str] = None

    class Config:
        use_enum_values = True
