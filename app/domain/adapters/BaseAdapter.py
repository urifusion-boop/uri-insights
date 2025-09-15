from typing import Optional
from app.domain.enums.lead_enum import LeadSourceEnum


class BaseAdapter:
    # @abstractmethod
    def to_lead(self) -> Optional[dict]:
        raise NotImplementedError

    # @abstractmethod
    def to_post(self) -> Optional[dict]:
        raise NotImplementedError

    # @abstractmethod
    def to_mention(self) -> Optional[dict]:
        raise NotImplementedError

    def map_platform_to_lead_source_enum(self, platform: str) -> LeadSourceEnum:
        lead_sources = {
            "reddit.com": LeadSourceEnum.REDDIT,
            "facebook.com": LeadSourceEnum.FACEBOOK,
            "twitter.com": LeadSourceEnum.X,
            "instagram.com": LeadSourceEnum.INSTAGRAM,
            "tiktok.com": LeadSourceEnum.TIKTOK,
            "linkedin.com": LeadSourceEnum.LINKEDIN,
            "x.com": LeadSourceEnum.X,
        }
        return lead_sources.get(platform, LeadSourceEnum.OTHER)

    def should_return_lead(self, lead_dict: dict):
        if lead_dict.get("text") is not None or lead_dict.get("title") is not None:
            return lead_dict
