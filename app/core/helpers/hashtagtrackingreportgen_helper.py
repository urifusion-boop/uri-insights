from collections import Counter
from typing import List, Optional
from app.core.helpers.date_helper import DateHelper
from app.core.helpers.reportgeneration_helper import ReportGenerationHelper
from app.core.helpers.text_helper import TextHelper
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.reportgeneration_enum import ReportGenSectionKeyEnum
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.repository.InfluencerRepository import InfluencerRepository
from app.services.GoogleService import GoogleService
from app.services.HashtagService import HashtagService
from app.services.uri_microservices.UriBackendService import UriBackendService
from motor.motor_asyncio import AsyncIOMotorDatabase


class HashtagTrackingReportGenHelper(ReportGenerationHelper):
    @staticmethod
    async def generate_string_for_cache_key(
        tracker_data: dict, period, included_fields: List[ReportGenSectionKeyEnum]
    ) -> str:
        included_fields_str: List[str] = [field.value for field in included_fields]
        result = f"{tracker_data.get('name')}-{period}-{','.join(included_fields_str)}"
        return result

    @staticmethod
    async def get_account_info(hashtag: str) -> dict:
        return {
            "account_info": {
                "hashtag": f"#{hashtag}",
            }
        }

    @staticmethod
    async def get_hashtag_data(db: AsyncIOMotorDatabase, hashtag: str):
        hashtag_cache_key = HashtagService._format_cache_key(hashtag)
        tracked_hashtag_data = await HashtagService._get_cached_data(
            db=db, cache_key=hashtag_cache_key
        )
        if tracked_hashtag_data:
            return tracked_hashtag_data
        raise Exception(
            f"This hashtag '{hashtag}' has not been tracked, please track it before generating a report."
        )

    @staticmethod
    async def get_post_report(db: AsyncIOMotorDatabase, hashtag: str):
        hashtag_post_report = (await HashtagService.fetch_post_report(db, hashtag)).get(
            "responseData", {}
        )

        return hashtag_post_report

    @staticmethod
    async def get_user_meta_access_token(
        db: AsyncIOMotorDatabase, user_id: str
    ) -> Optional[str]:
        user_influencers = (
            (
                await InfluencerRepository.get_influencers_by_filter(
                    db=db, user_id=user_id, platforms=[PostPlatformEnum.INSTAGRAM.value]
                )
            )
            .get("responseData", {})
            .get("data", [])
        )

        if not user_influencers:
            return None

        influencer_data = user_influencers[0]

        if not influencer_data:
            return None

        token = influencer_data.get("token")

        return token

    @staticmethod
    def construct_current_period_insights(
        posts: List[dict], report_timeframe: DateFilterEnum, hashtag: str
    ):
        current_period_posts = HashtagTrackingReportGenHelper.get_current_period_posts(
            posts=posts, report_timeframe=report_timeframe
        )
        if not current_period_posts or len(current_period_posts) == 0:
            raise ValueError("There is no new data for this period")
        insights = HashtagTrackingReportGenHelper.extract_insights_from_posts(
            current_period_posts, hashtag
        )

        return {"current_period_insights": insights}

    @staticmethod
    def construct_previous_period_insights(
        posts: List[dict], report_timeframe: DateFilterEnum, hashtag: str
    ):
        previous_period_posts = (
            HashtagTrackingReportGenHelper.get_previous_period_posts(
                posts=posts, report_timeframe=report_timeframe
            )
        )
        insights = HashtagTrackingReportGenHelper.extract_insights_from_posts(
            previous_period_posts, hashtag
        )

        return {"previous_period_insights": insights}

    @staticmethod
    def extract_insights_from_posts(posts: List[dict], hashtag: str):
        insights: dict = {
            "engagements": {},
            "likes": {},
            "comments": {},
            "mentions": {},
        }

        for post in posts:
            post_timestamp = DateHelper.to_readable_human_format(
                post.get("timestamp", "")
            )
            post_likes = post.get("like_count", 0)
            post_comments = post.get("comments_count", 0)
            post_engagements = post_likes + post.get("comments_count", 0)
            post_text = post.get("content", post.get("caption", ""))

            insights["engagements"][post_timestamp] = post_engagements
            insights["likes"][post_timestamp] = post_likes
            insights["comments"][post_timestamp] = post_comments
            insights["mentions"][post_timestamp] = (
                HashtagTrackingReportGenHelper.get_hashtag_mentions_from_post(
                    post_text, f"#{hashtag}"
                )
            )

            insights["engagements"] = dict(sorted(insights["engagements"].items()))
            insights["likes"] = dict(sorted(insights["likes"].items()))
            insights["comments"] = dict(sorted(insights["comments"].items()))
            insights["mentions"] = dict(sorted(insights["mentions"].items()))

        return insights

    # ---- KPI METRICS CALCULATIONS METHODS ----
    @staticmethod
    def get_total_mentions_kpi(
        posts: List[dict], hashtag: str, report_timeframe: DateFilterEnum
    ):
        current_posts = HashtagTrackingReportGenHelper.get_current_period_posts(
            posts, report_timeframe
        )
        previous_posts = HashtagTrackingReportGenHelper.get_previous_period_posts(
            posts, report_timeframe
        )
        current_total_mentions = HashtagTrackingReportGenHelper.get_hashtag_mentions(
            hashtag, current_posts
        )
        previous_total_mentions = HashtagTrackingReportGenHelper.get_hashtag_mentions(
            hashtag, previous_posts
        )

        total_mentions_kpi = HashtagTrackingReportGenHelper.construct_kpi_dict(
            "Total Hashtag Mentions", current_total_mentions, previous_total_mentions
        )

        return total_mentions_kpi

    @staticmethod
    def get_total_engagements_kpi(
        current_period_insights: dict, previous_period_insights: dict
    ):
        current_total_engagements = (
            HashtagTrackingReportGenHelper.get_total_engagements(
                current_period_insights
            )
        )
        previous_total_engagements = (
            HashtagTrackingReportGenHelper.get_total_engagements(
                previous_period_insights
            )
        )

        total_engagements_kpi = HashtagTrackingReportGenHelper.construct_kpi_dict(
            "Total Engagement", current_total_engagements, previous_total_engagements
        )

        return total_engagements_kpi

    @staticmethod
    def get_positive_sentiment_kpi(
        current_sentiment_analysis: dict, previous_sentiment_analysis: dict
    ):
        current_sentiment_summary = current_sentiment_analysis.get(
            "sentiment_summary", {}
        )
        previous_sentiment_summary = previous_sentiment_analysis.get(
            "sentiment_summary", {}
        )
        current = current_sentiment_summary.get("positive", 0)
        previous = previous_sentiment_summary.get("positive", 0)
        positive_sentiment_kpi = {
            "kpi": "Positive Sentiment (%)",
            "currentPeriod": f"{round(current, 2)}%",
            "previousPeriod": f"{round(previous, 2)}%",
            "change": f"{(current - previous):+0.2f}%",
        }

        return positive_sentiment_kpi

    @staticmethod
    def get_negative_sentiment_kpi(
        current_sentiment_analysis: dict, previous_sentiment_analysis: dict
    ):
        current_sentiment_summary = current_sentiment_analysis.get(
            "sentiment_summary", {}
        )
        previous_sentiment_summary = previous_sentiment_analysis.get(
            "sentiment_summary", {}
        )
        current = current_sentiment_summary.get("negative", 0)
        previous = previous_sentiment_summary.get("negative", 0)
        negative_sentiment_kpi = {
            "kpi": "Negative Sentiment (%)",
            "currentPeriod": f"{round(current, 2)}%",
            "previousPeriod": f"{round(previous, 2)}%",
            "change": f"{round((current - previous), 2)}%",
        }

        return negative_sentiment_kpi

    @staticmethod
    def get_post_distribution_type_kpi(
        current_post_type_distribution, previous_post_type_distribution
    ):
        current_top_post_type = "-"
        previous_top_post_type = "-"
        if current_post_type_distribution:
            current_top_post_type = max(
                current_post_type_distribution, key=current_post_type_distribution.get
            )
        if previous_post_type_distribution:
            previous_top_post_type = max(
                previous_post_type_distribution, key=previous_post_type_distribution.get
            )

        post_distribution_type_kpi = HashtagTrackingReportGenHelper.construct_kpi_dict(
            "Top Post Type", current_top_post_type, previous_top_post_type
        )

        return post_distribution_type_kpi

    @staticmethod
    async def get_sentiment_analysis(
        posts: List[dict], report_timeframe: DateFilterEnum
    ):
        current_posts = HashtagTrackingReportGenHelper.get_current_period_posts(
            posts, report_timeframe
        )
        previous_posts = HashtagTrackingReportGenHelper.get_previous_period_posts(
            posts, report_timeframe
        )
        current_sentiment_analysis = await GoogleService.analyze_comments_sentiment(
            current_posts, "caption"
        )
        previous_sentiment_analysis = await GoogleService.analyze_comments_sentiment(
            previous_posts, "caption"
        )

        return current_sentiment_analysis, previous_sentiment_analysis

    @staticmethod
    async def get_post_type_distribution(
        posts: List[dict], report_timeframe: DateFilterEnum
    ):
        current_posts = HashtagTrackingReportGenHelper.get_current_period_posts(
            posts, report_timeframe
        )
        previous_posts = HashtagTrackingReportGenHelper.get_previous_period_posts(
            posts, report_timeframe
        )
        current_post_type_distribution = dict(
            Counter(post["media_type"] for post in current_posts)
        )
        previous_post_type_distribution = dict(
            Counter(post["media_type"] for post in previous_posts)
        )
        return current_post_type_distribution, previous_post_type_distribution

    @staticmethod
    def get_hashtag_mentions(hashtag: str, posts: List[dict]):
        hashtag_count = 0
        if not hashtag or not posts:
            return hashtag_count
        hashtag = f"#{hashtag.lower()}"

        for post in posts:
            count = len(TextHelper.extract_hashtags(post.get("caption", ""), hashtag))
            hashtag_count += count

        return hashtag_count

    @staticmethod
    def get_total_engagements(insights):
        engagements: dict = insights.get("engagements", {})
        return sum(list(engagements.values()))

    @staticmethod
    def get_total_likes(insights):
        engagements: dict = insights.get("likes", {})
        return sum(list(engagements.values()))

    # ---- Helper Methods ----
    @classmethod
    def get_previous_period_posts(
        cls, posts: List[dict], report_timeframe: DateFilterEnum
    ):
        start_date, end_date = DateHelper.get_date_range(report_timeframe)
        period_length_days = end_date - start_date
        previous_start = start_date - period_length_days
        previous_period_posts = super().extract_previous_period_posts(
            posts=posts,
            split_date=start_date,
            limit_date=previous_start,
            time_key="timestamp",
        )
        return previous_period_posts

    @classmethod
    def get_current_period_posts(
        cls, posts: List[dict], report_timeframe: DateFilterEnum
    ):
        start_date, _ = DateHelper.get_date_range(report_timeframe)
        current_period_posts = super().extract_current_period_posts(
            posts=posts, split_date=start_date, time_key="timestamp"
        )
        return current_period_posts

    @staticmethod
    def get_hashtag_mentions_from_post(post_text: str, hashtag: str) -> int:
        hashtags = TextHelper.extract_hashtags(post_text, hashtag)
        return len(hashtags)
