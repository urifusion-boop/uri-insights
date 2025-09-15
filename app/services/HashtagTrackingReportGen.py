from typing import List, Optional, Set
from app.core.helpers.hashtagtrackingreportgen_helper import (
    HashtagTrackingReportGenHelper,
)
from app.domain.enums.reportgeneration_enum import (
    ReportGenSectionKeyEnum,
    ReportGenSectionMethodsEnum,
)
from app.domain.enums.tracker_enum import TrackerTypeEnum
from app.domain.requests.reportgeneration_requests import ReportGenerationRequest
from app.domain.responses.reportgeneration_response import PerformanceMetrics
from app.repository.TrackerRepository import TrackerRepository
from app.services.BaseReportGenService import (
    BaseReportGenerator,
)
from motor.motor_asyncio import AsyncIOMotorDatabase


class HashtagTrackingReportGenService(BaseReportGenerator):
    """
    Generator class for Hashtag Tracking report.
    Dynamically executes selected sections and returns the final model.
    """

    CACHE_TTL = 24
    EXTRA_SECTIONS = [
        (
            ReportGenSectionKeyEnum.ENGAGEMENTS_AND_LIKES.value,
            ReportGenSectionMethodsEnum.ENGAGEMENTS_AND_LIKES.value,
        ),
        (
            ReportGenSectionKeyEnum.POST_TYPE_DISTRIBUTION.value,
            ReportGenSectionMethodsEnum.POST_TYPE_DISTRIBUTION.value,
        ),
        (
            ReportGenSectionKeyEnum.HASHTAG_MENTIONS.value,
            ReportGenSectionMethodsEnum.HASHTAG_MENTIONS.value,
        ),
        (
            ReportGenSectionKeyEnum.RELATED_HASHTAGS.value,
            ReportGenSectionMethodsEnum.RELATED_HASHTAGS.value,
        ),
        (
            ReportGenSectionKeyEnum.TRENDING_HASHTAGS.value,
            ReportGenSectionMethodsEnum.TRENDING_HASHTAGS.value,
        ),
        (
            ReportGenSectionKeyEnum.SENTIMENT_ANALYSIS.value,
            ReportGenSectionMethodsEnum.SENTIMENT_ANALYSIS.value,
        ),
        (
            ReportGenSectionKeyEnum.RECENT_POSTS.value,
            ReportGenSectionMethodsEnum.RECENT_POSTS.value,
        ),
    ]

    def __init__(
        self,
        request: ReportGenerationRequest,
        db: AsyncIOMotorDatabase,
        cache_key: str,
        tracker_data: dict,
    ):
        super().__init__(db, request, cache_key)
        self.included_fields: Set = set(request.included_fields or [])
        self.tracker: dict = tracker_data
        self.hashtag_data: Optional[str] = None
        self.hashtag_sentiments: Optional[List[dict]] = None

    @classmethod
    async def async_init(
        cls, request: ReportGenerationRequest, db: AsyncIOMotorDatabase
    ):
        if not request.tracker_id:
            print("Tracker not found")
            raise ValueError("No hashtag tracker found for  report generation.")
        tracker_data = (
            await TrackerRepository.get_tracker_by_id(
                db=db,
                tracker_id=request.tracker_id,
            )
        ).get("responseData", {})
        if tracker_data:
            tracker_owner_id = tracker_data.get("user_id", "")
            tracker_type = tracker_data.get("tracker_type", "")

            # Confirm tracker to be a hashtag tracker
            if tracker_type != TrackerTypeEnum.HASHTAG.value:
                raise ValueError(
                    "A keyword tracker cannot be selected for hastag tracking report generation."
                )

            # Confirm that the user making the request is the owner of the hashtag tracker
            if tracker_owner_id != request.user_id:
                raise ValueError(
                    "This user is not authorized to generate a report for the selected hashtag."
                )

            cache_key = (
                await HashtagTrackingReportGenHelper.generate_string_for_cache_key(
                    tracker_data, request.period.value, request.included_fields
                )
            )
            if not cache_key:
                print(
                    "Hashtag tracker not found for cache key generation in hashtag tracking report gen"
                )
                raise ValueError(cls.HASHTAG_TRACKING_GENERIC_EXCEPTION_MESSAGE)

            return cls(request, db, cache_key, tracker_data)

    async def generate(self):
        return await super().generate()

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL", "metadata")
    async def _fetch_metadata(self):
        hashtag = self.tracker.get("name", "")
        account_info = await HashtagTrackingReportGenHelper.get_account_info(hashtag)
        hashtag_data = await HashtagTrackingReportGenHelper.get_hashtag_data(
            self.db, self.tracker.get("name", "")
        )
        if (
            ReportGenSectionKeyEnum.RELATED_HASHTAGS in self.request.included_fields
        ) or (
            ReportGenSectionKeyEnum.TRENDING_HASHTAGS in self.request.included_fields
        ):
            post_report = await HashtagTrackingReportGenHelper.get_post_report(
                self.db, self.tracker.get("name", "")
            )
        else:
            post_report = None
        current_period_insights = (
            HashtagTrackingReportGenHelper.construct_current_period_insights(
                hashtag_data.get("media", []), self.request.period, hashtag
            )
        )
        previous_period_insights = (
            HashtagTrackingReportGenHelper.construct_previous_period_insights(
                hashtag_data.get("media", []), self.request.period, hashtag
            )
        )
        current_sentiment_analysis, previous_sentiment_analysis = (
            await HashtagTrackingReportGenHelper.get_sentiment_analysis(
                hashtag_data.get("media", []), self.request.period
            )
        )
        current_post_type_distribution, previous_post_type_distribution = (
            await HashtagTrackingReportGenHelper.get_post_type_distribution(
                hashtag_data.get("media", []), self.request.period
            )
        )
        metadata = {
            **account_info,
            **current_period_insights,
            **previous_period_insights,
            "post_data": hashtag_data.get("media", []),
            "hashtag_data": hashtag_data,
            "post_report": post_report,
            "current_sentiment_analysis": current_sentiment_analysis,
            "previous_sentiment_analysis": previous_sentiment_analysis,
            "current_post_type_distribution": current_post_type_distribution,
            "previous_post_type_distribution": previous_post_type_distribution,
        }

        self.metadata = metadata

        return metadata

    @HashtagTrackingReportGenHelper.cache_result(
        "CACHE_TTL",
        "account_info",
        custom_key_func=lambda self: f"{self.request.recipient}",
    )
    async def get_account_info(self):
        return await super().get_account_info()

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_overview(self):
        return await super().get_overview()

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_highlights(self):
        return await super().get_highlights()

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL", "performance_metrics")
    async def get_performance_metrics(self):
        performance_section_text = await super().get_performance_metrics()

        performance_metrics = await self.calculate_performance_metrics()

        result = PerformanceMetrics(
            text=performance_section_text, kpis=performance_metrics
        )

        self.performance_metrics = result

        return result

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_kpi_analysis(self):
        return await super().get_kpi_analysis()

    async def get_key_metrics(self):
        total_posts = len(self.metadata.get("post_data", []))
        total_engagements = HashtagTrackingReportGenHelper.get_total_engagements(
            self.metadata.get("current_period_insights")
        )
        total_likes = HashtagTrackingReportGenHelper.get_total_likes(
            self.metadata.get("current_period_insights")
        )
        post_type_distribution = self.metadata.get("current_post_type_distribution")
        top_post_type = "-"
        if post_type_distribution:
            top_post_type = max(post_type_distribution, key=post_type_distribution.get)
        total_mentions = HashtagTrackingReportGenHelper.get_hashtag_mentions(
            self.tracker.get("name", ""), self.metadata.get("post_data", [])
        )
        return {
            "totalPosts": total_posts,
            "totalEngagements": total_engagements,
            "totalLikes": total_likes,
            "totalComments": (total_engagements - total_likes),
            "topPostType": top_post_type,
            "totalMentions": total_mentions,
        }

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_ai_recommendations(self):
        return await super().get_ai_recommendations()

    # -------- METHODS TO GENERATE SECTIONS SPECIFIC TO HASHTAG TRACKING REPORT -----------
    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_engagements_and_likes(self):
        current_period_insights = self.metadata.get("current_period_insights", {})
        engagements: dict = current_period_insights.get("engagements", {})
        likes: dict = current_period_insights.get("likes", {})
        comments: dict = current_period_insights.get("comments", {})
        mentions: dict = current_period_insights.get("mentions", {})
        result = {}

        for key in list(engagements.keys()):
            result[key] = {
                "engagements": engagements.get(key, 0),
                "likes": likes.get(key, 0),
                "comments": comments.get(key, 0),
                "mentions": mentions.get(key, 0),
            }

        return result

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_post_type_distribution(self):
        return self.metadata.get("current_post_type_distribution")

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_hashtag_mentions(self):
        hashtag_data = self.metadata.get("hashtag_data", {})
        return hashtag_data.get("hashtag_mention_frequency")

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_related_hashtags(self):
        return self.metadata.get("post_report", {}).get("related_hashtags")

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_trending_hashtags(self):
        return self.metadata.get("post_report", {}).get("trending_hashtags")

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_sentiment_analysis(self):
        return self.metadata.get("current_sentiment_analysis", {}).get(
            "sentiment_summary"
        )

    @HashtagTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_recent_posts(self):
        posts = self.metadata.get("current_sentiment_analysis", {}).get(
            "comments_with_sentiment", []
        )[:5]
        filtered_posts = [
            {k: v for k, v in post.items() if k != "children"} for post in posts
        ]
        return filtered_posts

    async def calculate_performance_metrics(self):
        post_data = self.metadata.get("post_data", [{}])
        hashtag = self.tracker.get("name", "")
        report_timeframe = self.request.period
        peformance_metrics = [
            HashtagTrackingReportGenHelper.get_total_mentions_kpi(
                post_data, hashtag, report_timeframe
            ),
            HashtagTrackingReportGenHelper.get_total_engagements_kpi(
                self.metadata.get("current_period_insights"),
                self.metadata.get("previous_period_insights"),
            ),
            HashtagTrackingReportGenHelper.get_positive_sentiment_kpi(
                self.metadata.get("current_sentiment_analysis"),
                self.metadata.get("previous_sentiment_analysis"),
            ),
            HashtagTrackingReportGenHelper.get_negative_sentiment_kpi(
                self.metadata.get("current_sentiment_analysis"),
                self.metadata.get("previous_sentiment_analysis"),
            ),
            HashtagTrackingReportGenHelper.get_post_distribution_type_kpi(
                self.metadata.get("current_post_type_distribution"),
                self.metadata.get("previous_post_type_distribution"),
            ),
        ]

        return peformance_metrics
