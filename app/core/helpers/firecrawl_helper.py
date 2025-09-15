from datetime import datetime
from typing import Optional
from app.domain.enums.domain_enum import DomainEnum
from app.domain.requests.firecrawl_requests import FirecrawlParams


class FirecrawlHelper:
    @staticmethod
    def construct_firecrawl_input(business_info: dict) -> dict:
        params = {
            "domains": business_info.get("domains", [DomainEnum.NAIRALAND.value]),
            "keywords": business_info.get("keywords", []),
            "time_frame": FirecrawlHelper.__get_time_frame(
                business_info.get("last_scraped_date")
            ),
        }
        return {
            "user_id": business_info.get("user_id"),
            "params": params,
            "platform": "firecrawl",
        }

    @staticmethod
    def __get_time_frame(last_scraped_date: Optional[datetime]) -> str:
        if last_scraped_date:
            time_frame = (datetime.now() - last_scraped_date).days
            if time_frame > 30:
                return "last 30 days"
            return f"last {time_frame} days"
        return "last 30 days"
