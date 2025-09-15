from typing import List, Optional

from app.domain.adapters.BaseAdapter import BaseAdapter
from app.domain.enums.lead_enum import LeadStatusEnum
from app.domain.enums.sentiment_enum import SentimentEnum


class MentionAdapter(BaseAdapter):
    def __init__(self, data: dict):
        self.data = data

    def to_lead(self):
        data = self.data
        lead_dict = {
            "title": data.get("title"),
            "text": data.get("comment"),
            "username": data.get("author"),
            "lead_source": self.map_platform_to_lead_source_enum(
                data.get("platform")
            ).value,
            "lead_status": LeadStatusEnum.NEW.value,
        }
        return self.should_return_lead(lead_dict)

    def to_post(self):
        return self.data

    def to_mention(self):
        return self.data

    @staticmethod
    def adapt_instagram_comment_to_mention(
        posts_data: List[dict],
    ) -> Optional[List[dict]]:
        adapted_posts = []

        for post in posts_data:
            influencer_data = post.get("influencer_data")
            comment_data = post.get("comment_data")
            if not influencer_data:
                print("Influencer data is missing")
                influencer_data = {"data": "Dummy data"}
                # return None
            if not comment_data:
                print("Comment data is missing")
                comment_data = {"data": "Dummy data"}
                # return None
            username = comment_data.get("username")
            if not username:
                username = comment_data.get("from", {}).get("username", "just_inlight")
            adapted_post = {
                "user_id": influencer_data.get("user_id", "6735e2e02a610392a70e934b"),
                "keyword": post.get("keyword", "Data Insights"),
                "comment": comment_data.get(
                    "text",
                    "The new age will be defined by those who can take advantage of data and generate profitable insights",
                ),
                "author": f"https://www.instagram.com/{username}/",
                "timestamp": comment_data.get("timestamp", "2025-03-11T10:24:02+0000"),
                "platform": "INSTAGRAM",
                "sentiment": post.get("sentiment", SentimentEnum.POSITIVE),
                "sentiment_score": post.get("sentiment_score", 0.8980998),
                "sentiment_priority": post.get("sentiment_priority"),
            }
            adapted_posts.append(adapted_post)

        return adapted_posts
