from typing import List, Optional
from pydantic import BaseModel


class FirecrawlParams(BaseModel):
    domains: List[str]
    keywords: List[str] | str
    entity: str
    crawl_schema: dict
    extract_field: str
    time_frame: Optional[str] = "last 7 days"
