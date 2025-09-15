import asyncio
from typing import Any, List, Optional, Tuple
from app.core.helpers.date_helper import DateHelper
from app.core.helpers.reportgeneration_helper import ReportGenerationHelper
from app.core.helpers.text_helper import TextHelper
from app.domain.enums.date_enum import DateFilterEnum
from app.repository.InfluencerRepository import InfluencerRepository
from app.services.GoogleService import GoogleService
from motor.motor_asyncio import AsyncIOMotorDatabase


class AccountTrackingReportGenHelper(ReportGenerationHelper):
    @staticmethod
    def process_hashtag_frequency_dict(data: dict) -> dict:
        dict_values = data.values()
        maximum_freq = max(dict_values)
        result_dict = {}
        for key, value in data.items():
            result_dict[key] = round((value / maximum_freq) * 100, 2)
        return result_dict

    @staticmethod
    async def extract_total_posts_sentiments_and_hashtag_kpi(
        post_data: List[dict], report_period: DateFilterEnum
    ) -> Tuple[Any, Any, Any]:
        start_date, end_date = DateHelper.get_date_range(report_period)
        period_length_days = end_date - start_date
        previous_start = start_date - period_length_days
        current_posts = AccountTrackingReportGenHelper.extract_current_period_posts(
            post_data, start_date
        )
        previous_posts = AccountTrackingReportGenHelper.extract_previous_period_posts(
            post_data, start_date, previous_start
        )

        positive_sentiment_kpi = (
            await AccountTrackingReportGenHelper.__extract_positive_sentiment_kpi(
                current_posts, previous_posts
            )
        )

        top_performing_hashtag_kpi = (
            await AccountTrackingReportGenHelper.__extract_top_performing_hashtag_kpi(
                current_posts, previous_posts
            )
        )

        current = len(current_posts)
        previous = len(previous_posts)
        total_posts_kpi = AccountTrackingReportGenHelper.construct_kpi_dict(
            "Total Posts", current, previous
        )
        return (total_posts_kpi, positive_sentiment_kpi, top_performing_hashtag_kpi)

    @staticmethod
    async def __extract_positive_sentiment_kpi(
        current_posts: List[dict], previous_posts: List[dict]
    ):
        current_posts_sentiment_analytics = (
            await GoogleService.analyze_comments_sentiment(current_posts, "content")
        )
        previous_posts_sentiment_analytics = (
            await GoogleService.analyze_comments_sentiment(previous_posts, "content")
        )

        current = current_posts_sentiment_analytics.get("sentiment_summary", {}).get(
            "positive", 0
        )
        previous = previous_posts_sentiment_analytics.get("sentiment_summary", {}).get(
            "positive", 0
        )

        result = {
            "kpi": "Positive Sentiment",
            "currentPeriod": f"{round(current, 2)}%",
            "previousPeriod": f"{round(previous, 2)}%",
            "change": f"{round((current - previous), 2)}%",
        }
        return result

    @staticmethod
    async def __extract_top_performing_hashtag_kpi(
        current_posts: List[dict], previous_posts: List[dict]
    ):
        current_top_performing_hashtags = TextHelper.compute_hashtag_frequency(
            current_posts, "caption"
        )
        previous_top_performing_hashtags = TextHelper.compute_hashtag_frequency(
            previous_posts, "caption"
        )

        if current_top_performing_hashtags:
            current_top_performing_hashtag = current_top_performing_hashtags[0].get(
                "hashtag", "-"
            )
        else:
            current_top_performing_hashtag = "-"
        if previous_top_performing_hashtags:
            previous_top_performing_hashtag = previous_top_performing_hashtags[0].get(
                "hashtag", "-"
            )
        else:
            previous_top_performing_hashtag = "-"

        result = AccountTrackingReportGenHelper.construct_kpi_dict(
            "Top Performing Hashtag",
            current_top_performing_hashtag,
            previous_top_performing_hashtag,
        )
        return result

    @staticmethod
    def extract_total_engagements_kpi(metadata: dict) -> Optional[dict]:
        current_period_insights = metadata.get("current_period_insights")
        previous_period_insights = metadata.get("previous_period_insights")

        if not current_period_insights or not previous_period_insights:
            raise ValueError(
                "Current or previous period insights not found for followers growth KPI generation"
            )

        current_engagements = current_period_insights.get("engagements")
        previous_engagements = previous_period_insights.get("engagements")

        if not current_engagements or not previous_engagements:
            raise ValueError(
                "Current or Previous engagements are missing for KPI generation"
            )
        current = sum(current_engagements.values())
        previous = sum(previous_engagements.values())

        result = AccountTrackingReportGenHelper.construct_kpi_dict(
            "Total Engagements", current, previous
        )
        return result

    @staticmethod
    def extract_engagement_rate_kpi(metadata: dict) -> dict:
        current_period_insights, previous_period_insights = (
            AccountTrackingReportGenHelper.get_period_insights(metadata)
        )

        current = AccountTrackingReportGenHelper._calculate_engagement_rate(
            current_period_insights
        )
        previous = AccountTrackingReportGenHelper._calculate_engagement_rate(
            previous_period_insights
        )

        percentage_change_str = (
            AccountTrackingReportGenHelper._format_percentage_change(current - previous)
        )

        return {
            "kpi": "Engagement Rate",
            "currentPeriod": f"{round(current, 2)}%",
            "previousPeriod": f"{round(previous, 2)}%",
            "change": percentage_change_str,
        }

    @staticmethod
    def _calculate_engagement_rate(period_insights: dict) -> float:
        engagements = period_insights.get("engagements")
        impressions = period_insights.get("impressions")

        if not engagements or not impressions:
            return 0.0

        total_engagements = sum(engagements.values())
        total_impressions = sum(impressions.values())

        if total_engagements == 0 or total_impressions == 0:
            return 0.0

        # Fix possible data inconsistency
        if total_impressions < total_engagements:
            total_impressions += total_engagements

        # Engagement rate calculation (as percentage)
        rate = ((total_impressions - total_engagements) / total_impressions) * 100
        return rate

    @staticmethod
    def _format_percentage_change(change: float) -> str:
        rounded_change = round(change, 2)
        if rounded_change > 0:
            return f"+{rounded_change}%"
        return f"{rounded_change}%"

    @staticmethod
    def extract_followers_growth_kpi(metadata: dict) -> Optional[dict]:
        current_period_insights = metadata.get("current_period_insights")
        previous_period_insights = metadata.get("previous_period_insights")

        if not current_period_insights or not previous_period_insights:
            raise ValueError(
                "Current or previous period insights not found for followers growth KPI generation"
            )
        current_followers = current_period_insights.get("followers", {})
        previous_followers = previous_period_insights.get("followers", {})

        current = sum(current_followers.values()) if current_followers else 0
        previous = sum(previous_followers.values()) if previous_followers else 0

        result = AccountTrackingReportGenHelper.construct_kpi_dict(
            "Followers Growth", current, previous
        )
        return result

    @staticmethod
    async def generate_string_for_cache_key(
        db: AsyncIOMotorDatabase, influencer_ids: dict, period
    ) -> Optional[str]:
        get_influencer_data_tasks = [
            InfluencerRepository.get_influencer_specific_data_by_influencer_id(
                db=db,
                influencer_id=influencer_id,
                fields=["social_platform", "social_user_id"],
            )
            for influencer_id in influencer_ids.values()
        ]
        influencer_data = await asyncio.gather(*get_influencer_data_tasks)
        if influencer_data:
            platforms = [
                data.get("social_platform") for data in influencer_data if data
            ]
            social_user_ids = [
                data.get("social_user_id") for data in influencer_data if data
            ]
            result = f"{','.join(social_user_ids)}-{','.join(platforms)}-{period}"
            return result
        return None
