from datetime import datetime, timedelta, timezone
from typing import List
from app.domain.adapters.ReportGenAdapter import ReportGenAdapter


class InstagramAdapter(ReportGenAdapter):
    def __init__(self, data: dict):
        self.data = data

    def to_report_gen_metadata(self):
        current_period_insights = self.data.get("current_period_insights")
        previous_period_insights = self.data.get("previous_period_insights")
        account_info = self.data.get("account_info")

        posts = account_info.get("media", {}).get("data", [])

        posts = self.adapt_posts_structure(posts)

        metadata = {
            "account_info": self.extract_account_info_instagram(account_info),
            "current_period_insights": self.instagram_data_to_metadata_section(
                current_period_insights, posts
            ),
            "previous_period_insights": self.instagram_data_to_metadata_section(
                previous_period_insights, posts
            ),
            "post_data": posts,
        }
        return metadata

    def adapt_posts_structure(self, posts: List[dict]):
        for item in posts:
            if item.get("media_url"):
                del item["media_url"]
            item["post_time"] = item["timestamp"]
            del item["timestamp"]
            item["engagement_count"] = item["like_count"]
            item["comment_count"] = item["comments_count"]
            del item["like_count"]
            del item["comments_count"]
        return posts

    def extract_account_info_instagram(self, data: dict) -> dict:
        return {
            "name": data.get("username"),
            "username": data.get("username"),
            "followers_count": data.get("followers_count"),
        }

    def instagram_data_to_metadata_section(self, raw_insights_data, post_data):
        reach_data = None
        demographics_data = None
        followers_data = None
        sum_followers = 0

        for data in raw_insights_data:
            if isinstance(data, dict):
                if data.get("name") == "reach":
                    reach_data = data.get("values")
                elif data.get("name") == "follows_and_unfollows":
                    followers_data = data.get("total_value")

        if len(raw_insights_data) == 3:
            demographics_data = raw_insights_data[2]

        insights_dict = self.create_meta_insights_dict(
            impressions_data=reach_data,
            viewers_data=reach_data,
        )

        if demographics_data:
            insights_dict["audience_location"] = {
                item["dimension_values"][0]: item["value"]
                for item in demographics_data
                if item.get("dimension_values") and len(item["dimension_values"]) > 0
            }
        if followers_data:
            sum_followers = followers_data.get("follows", 0) + followers_data.get(
                "unfollows", 0
            )
        insights_dict["followers"] = {
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000"): sum_followers
        }
        insights_dict["engagements"] = self.extract_engagement_data_from_posts(
            post_data
        )

        return insights_dict

    def extract_engagement_data_from_posts(self, posts):
        since = self.data.get("since")
        until = self.data.get("until")

        if not since or not until:
            raise ValueError("Period data not provided for Instagram report generation")

        # Initialize all days in range with 0
        daily_engagements = {
            (since + timedelta(days=i))
            .replace(hour=8, minute=0, second=0, microsecond=0)
            .isoformat(timespec="microseconds")
            + "Z": 0
            for i in range((until - since).days + 1)
        }

        for post in posts:
            ts = datetime.fromisoformat(post["post_time"]).replace(tzinfo=None)

            # Only include posts within the since-until range
            if since <= ts <= until:
                day_key = (
                    ts.replace(hour=8, minute=0, second=0, microsecond=0).isoformat(
                        timespec="microseconds"
                    )
                    + "Z"
                )
                engagement = post.get("engagement_count", 0) + post.get(
                    "comment_count", 0
                )
                daily_engagements[day_key] += engagement

        return daily_engagements
