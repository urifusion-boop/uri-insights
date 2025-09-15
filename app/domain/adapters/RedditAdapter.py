from typing import Optional
from app.domain.adapters.BaseAdapter import BaseAdapter
from app.domain.enums.lead_enum import LeadSourceEnum, LeadStatusEnum


class RedditAdapter(BaseAdapter):
    def __init__(self, data: dict):
        self.data = data

    def to_lead(self) -> dict:
        data = self.data.get("data", {})
        title = data.get("title")
        username = data.get("author")
        reddit_text = self.__process_reddit_text(data.get("selftext") or title)
        lead_dict = {
            "title": title,
            "text": reddit_text,
            "username": username,
            "lead_source": LeadSourceEnum.REDDIT.value,
            "lead_status": LeadStatusEnum.NEW.value,
            "social_profile": f"https://www.reddit.com/user/{username}",
            "social_profile_link": f"https://www.reddit.com/user/{username}",
            "lead_link": data.get("url"),
        }
        return self.should_return_lead(lead_dict)

    def to_post(self) -> dict:
        return self.data

    def to_mention(self) -> dict:
        return self.data

    def __process_reddit_text(self, text: str, limit: int = 200) -> str:
        return text[:limit].rstrip() + "..." if len(text) > limit else text
