import re
from typing import Optional
from urllib.parse import urlparse
from app.core.helpers.text_helper import TextHelper
from app.domain.adapters.BaseAdapter import BaseAdapter
from app.domain.enums.lead_enum import LeadSourceEnum, LeadStatusEnum
from app.domain.models.keyword_model import (
    AuthorModel,
    PublicMetricsModel,
    SocialMediaPostTrackedItem,
)
from app.core.helpers.google_helper import GoogleHelper


class GoogleAdapter(BaseAdapter):
    def __init__(self, data: dict):
        self.data = data

    def to_lead(self) -> Optional[dict]:
        influencer = self.__extract_influencer_from_web_data_item(self.data)
        lead_dict = {
            "title": self.data.get("title"),
            "text": self.data.get("snippet"),
            "username": influencer.name if influencer else None,
            "lead_source": self.map_platform_to_lead_source_enum(
                self.__extract_platform(self.data)
            ).value,
            "lead_status": LeadStatusEnum.NEW.value,
            "social_profile": influencer.link if influencer else None,
            "social_profile_link": influencer.link if influencer else None,
            "lead_link": self.data.get("link"),
        }
        return self.should_return_lead(lead_dict)

    def to_post(self) -> dict:
        platform = self.__extract_platform(self.data)
        influencer = self.__extract_influencer_from_web_data_item(self.data)
        engagements = self.__get_post_engagement_data_from_web_tracker_data(
            self.data.get("pagemap", {}).get("interactioncounter")
        )
        post = {
            "id": self.__extract_post_id(self.data.get("link")),
            "platform": platform,
            "title": self.data.get("title", ""),
            "text": self.data.get("snippet", ""),
            "htmlTitle": self.data.get("htmlTitle", ""),
            "htmlSnippet": self.data.get("htmlSnippet", ""),
            "snippet": self.data.get("snippet", ""),
            "htmlFormattedUrl": self.data.get("htmlFormattedUrl", ""),
            "formattedUrl": self.data.get("formattedUrl", ""),
            "displayLink": self.data.get("displayLink", ""),
            "link": self.data.get("link", ""),
            "pagemap": self.data.get("pagemap", {}),
            "author": influencer.dict(exclude_none=True) if influencer else None,
            "public_metrics": (
                engagements.dict(exclude_none=True) if engagements else None
            ),
            "timestamp": GoogleHelper.get_timestamp_from_search(self.data),
        }
        post_object = SocialMediaPostTrackedItem(**post)
        return post_object.dict(exclude_none=True)

    def to_mention(self) -> dict:
        return self.data

    def __extract_platform(self, post: dict) -> str:
        valid_social_websites = [
            "reddit.com",
            "facebook.com",
            "youtube.com",
            "twitter.com",
            "instagram.com",
            "tiktok.com",
            "linkedin.com",
            "threads.net",
            "x.com",
            "snapchat.com",
            "pinterest.com",
        ]
        link = post.get("link", "")
        parsed_url = urlparse(link).netloc
        domain_name = ".".join(str(parsed_url).split(".")[1:])
        platform = "web"
        if domain_name in valid_social_websites or parsed_url in valid_social_websites:
            platform = (
                domain_name if domain_name in valid_social_websites else parsed_url
            )
        return platform

    def __get_post_engagement_data_from_web_tracker_data(
        self,
        data: dict,
    ) -> Optional[PublicMetricsModel]:
        if data:
            engagement_data = {}
            for counter in data:
                if "url" in counter.keys():
                    if counter.get("name") == "Likes":
                        engagement_data["like_count"] = int(
                            counter.get("userinteractioncount", 0)
                        )
                    elif counter.get("name") == "Retweets":
                        engagement_data["retweet_count"] = int(
                            counter.get("userinteractioncount", 0)
                        )
                    elif counter.get("name") == "Quotes":
                        engagement_data["quote_count"] = int(
                            counter.get("userinteractioncount", 0)
                        )
                    elif counter.get("name") == "Replies":
                        engagement_data["reply_count"] = int(
                            counter.get("userinteractioncount", 0)
                        )
            engagement = PublicMetricsModel(**engagement_data)
            return engagement
        return None

    def __extract_post_id(self, url) -> Optional[str]:
        """
        Extracts the post ID from a given social media URL, handling trailing slashes.
        """
        if url:
            match = re.search(r"(?:story_fbid=|status/)([/d]+)", url.rstrip("/"))
            return match.group(1) if match else None
        return None

    def __extract_influencer_from_web_data_item(
        self, item: dict
    ) -> Optional[AuthorModel]:
        """Extract influencer details from web data item."""
        if isinstance(item, dict):
            pagemap = item.get("pagemap", {})
            metatags = pagemap.get("metatags", [{}])[0] or {}
            person = pagemap.get("person", [{}])[0] or {}

            influencer_types = ["author", "creator", "publisher"]

            # Extract initial values
            name = person.get("givenname", "")
            author_id = person.get("id", "")

            if not metatags:
                return None

            for key, value in metatags.items():
                if any(influencer_type in key for influencer_type in influencer_types):
                    name = value if not name else name
                    link = ""
                    type_ = "author" if "author" in key else "publisher"

                    if TextHelper.is_url(name):
                        link = name
                        name = name.split("/")[-1]

                    if name:
                        return AuthorModel(
                            id=author_id, type=type_, name=name, link=link or None
                        )

        return None  # No influencer data fo
