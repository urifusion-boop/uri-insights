import asyncio
from typing import Any, Callable, Dict, Iterable, Optional, Tuple
from app.core.helpers.accounttrackingreportgen_helper import (
    AccountTrackingReportGenHelper,
)
from app.core.helpers.date_helper import DateHelper
from app.core.helpers.text_helper import TextHelper
from app.domain.enums.reportgeneration_enum import (
    ReportGenSectionKeyEnum,
    ReportGenSectionMethodsEnum,
)
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.requests.reportgeneration_requests import (
    MultiAccReportGenericType,
    ReportGenerationRequest,
)
from app.domain.responses.reportgeneration_response import (
    AIIndustryClassification,
    ActivityOverview,
    KeyMetrics,
    PerformanceMetrics,
    SummaryAndAchievement,
)
from app.domain.strategies.ReportGenMetadataStrategies.account_tracking_metadata_strategies import (
    PLATFORM_METADATA_FETCHERS,
)
from app.services.BaseReportGenService import (
    BaseReportGenerator,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.ReportGenAiService import ReportGenAiService


class AccountTrackingReportGenService(BaseReportGenerator):
    """
    Generator class for Account Tracking report.
    Dynamically executes selected sections and returns the final model.
    """

    CACHE_TTL = 24
    EXTRA_SECTIONS = [
        (
            ReportGenSectionKeyEnum.AUDIENCE_LOCATION.value,
            ReportGenSectionMethodsEnum.AUDIENCE_LOCATION.value,
        ),
        (
            ReportGenSectionKeyEnum.ENGAGEMENT_OVER_TIME.value,
            ReportGenSectionMethodsEnum.ENGAGEMENT_OVER_TIME.value,
        ),
        (
            ReportGenSectionKeyEnum.LAST_25_POSTS.value,
            ReportGenSectionMethodsEnum.LAST_25_POSTS.value,
        ),
        (
            ReportGenSectionKeyEnum.MOST_USED_HASHTAGS.value,
            ReportGenSectionMethodsEnum.MOST_USED_HASHTAGS.value,
        ),
        (
            ReportGenSectionKeyEnum.SUMMARY_AND_ACHIEVEMENT.value,
            ReportGenSectionMethodsEnum.SUMMARY_AND_ACHIEVEMENT.value,
        ),
        (
            ReportGenSectionKeyEnum.ACTIVITY_OVERVIEW.value,
            ReportGenSectionMethodsEnum.ACTIVITY_OVERVIEW.value,
        ),
        (
            ReportGenSectionKeyEnum.AI_INDUSTRY_CLASSIFICATION.value,
            ReportGenSectionMethodsEnum.AI_INDUSTRY_CLASSIFICATION.value,
        ),
        (
            ReportGenSectionKeyEnum.TOP_SUGGESTED_IMPROVEMENT.value,
            ReportGenSectionMethodsEnum.TOP_SUGGESTED_IMPROVEMENT.value,
        ),
    ]

    EXTRA_MANDATORY_SECTIONS = {
        ReportGenSectionKeyEnum.ACTIVITY_OVERVIEW.value,
        ReportGenSectionKeyEnum.MOST_USED_HASHTAGS.value,
        ReportGenSectionKeyEnum.AI_INDUSTRY_CLASSIFICATION.value,
        ReportGenSectionKeyEnum.RECOMMENDATIONS.value,
    }

    def __init__(
        self, request: ReportGenerationRequest, db: AsyncIOMotorDatabase, cache_key: str
    ):
        super().__init__(db, request, cache_key)
        self.included_fields = set(request.included_fields or [])

    @classmethod
    async def async_init(
        cls, request: ReportGenerationRequest, db: AsyncIOMotorDatabase
    ):
        if request.influencer_ids:
            cache_key = (
                await AccountTrackingReportGenHelper.generate_string_for_cache_key(
                    db, request.influencer_ids.model_dump(), request.period.value
                )
            )
            if not cache_key:
                print(
                    "Influencer not found for cache key generation in account tracking report gen"
                )
                raise ValueError(cls.ACCOUNT_TRACKING_GENERIC_EXCEPTION_MESSAGE)

            return cls(request, db, cache_key)

    async def generate(self):
        return await super().generate()

    async def fetch_platform_metadata(
        db: Any,
        request: Any,
        subtypes: Iterable[Any],
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Fetch metadata for each subtype concurrently.

        Args:
            db: DB handle/connection/session.
            request: Request object passed to fetchers.
            subtypes: Iterable of Enum-like items with a `.value` (e.g., INSTAGRAM).

        Returns:
            (metadata, errors)
            metadata: { "<subtype-lc>": <metadata> } only for successful fetches
            errors:   { "<subtype-lc>": "<error message>" } for failures or unsupported subtypes

        Behavior:
            - Runs every fetcher concurrently.
            - Never raises just because one fetcher failed.
            - Preserves subtype association in results.
        """

        # Build ordered list of (key, fetcher) pairs to preserve mapping order.
        entries: list[tuple[str, Callable[..., Any]]] = []
        unsupported: list[str] = []

        for st in subtypes:
            # Defensive: support both Enum-like objects and plain strings
            raw = getattr(st, "value", st)
            key = str(raw).lower()
            fetcher = PLATFORM_METADATA_FETCHERS.get(raw)
            if fetcher is None:
                unsupported.append(key)
                continue
            entries.append((key, fetcher))

        if not entries and unsupported:
            # Everything provided was unsupported; no point continuing
            raise ValueError(
                f"Unsupported platform subtype(s): {', '.join(unsupported)}"
            )

        # Kick off all fetchers concurrently
        tasks = [fetcher(db, request) for _, fetcher in entries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        metadata: Dict[str, Any] = {}
        errors: Dict[str, str] = {}

        # Pair each result back to its subtype key
        for (key, _), result in zip(entries, results):
            if isinstance(result, Exception):
                errors[key] = f"{type(result).__name__}: {result}"
                continue
            metadata[key] = result

        # Record any subtypes that had no registered fetcher
        for key in unsupported:
            errors[key] = "Unsupported subtype (no fetcher registered)"

        return metadata, errors

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL", "metadata")
    async def _fetch_metadata(self):
        """
        Platform-dispatched metadata loader.
        """
        subtypes = self.request.report_generation_subtypes

        if not self.request.influencer_ids:
            raise Exception(
                "Influencer IDs not provided for account tracking report gen."
            )

        metadata, errors = (
            await AccountTrackingReportGenService.fetch_platform_metadata(
                self.db, self.request, subtypes
            )
        )

        self.metadata = metadata

        return metadata

    @AccountTrackingReportGenHelper.cache_result(
        "CACHE_TTL",
        "account_info",
        custom_key_func=lambda self: f"{self.request.recipient}",
    )
    async def get_account_info(self):
        return await super().get_account_info()

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_overview(self):
        return await super().get_overview()

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_highlights(self):
        return await super().get_highlights()

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL", "performance_metrics")
    async def get_performance_metrics(self) -> Optional[PerformanceMetrics]:
        performance_section_text = await super().get_performance_metrics()

        performance_metrics = await self.calculate_performance_metrics()

        result = PerformanceMetrics(
            text=performance_section_text, kpis=performance_metrics
        )

        self.performance_metrics = result

        return result

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_kpi_analysis(self):
        return await super().get_kpi_analysis()

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_key_metrics(
        self,
    ) -> Optional[MultiAccReportGenericType[KeyMetrics, KeyMetrics, KeyMetrics]]:
        report_key_metrics = {}

        if not self.metadata:
            raise Exception("Metadata not provided for generating key metrics.")

        for platform, platform_metadata in self.metadata.items():
            # Extract insights using helper
            current_period_insights, _ = (
                AccountTrackingReportGenHelper.get_period_insights(platform_metadata)
            )

            account_info = platform_metadata.get("account_info", {})
            post_data = platform_metadata.get("post_data", [])

            # If account info or insights are missing, skip
            if not account_info or not current_period_insights:
                continue

            platform_report = {
                "totalFollowers": account_info.get("followers_count", 0),
                "totalFollowing": account_info.get("following_count", 0),
                "totalViewers": sum(
                    current_period_insights.get("viewers", {}).values()
                ),
                "totalPosts": len(post_data),
                "totalEngagements": sum(
                    current_period_insights.get("engagements", {}).values()
                ),
            }

            report_key_metrics[platform] = KeyMetrics(**platform_report)

        return MultiAccReportGenericType[KeyMetrics, KeyMetrics, KeyMetrics](
            instagram=report_key_metrics.get("instagram"),
            facebook=report_key_metrics.get("facebook"),
            linkedin=report_key_metrics.get("linkedin"),
        )

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_ai_recommendations(self):
        return await super().get_ai_recommendations()

    # ----- METHODS TO GET METRICS SPECIFIC TO ACCOUNT TRACKING REPORT -----
    # @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_engagement_over_time(self):
        report_engagement_over_time = {}

        for platform, platform_metadata in self.metadata.items():
            current_period_insights, _ = (
                AccountTrackingReportGenHelper.get_period_insights(platform_metadata)
            )

            platform_report = {}
            reach = current_period_insights.get("viewers", {})
            impressions = current_period_insights.get("impressions", {})

            for key in set(reach.keys()) | set(impressions.keys()):  # union of keys
                platform_report[DateHelper.to_readable_human_format(key)] = {
                    "reach": reach.get(key, 0),
                    "impressions": impressions.get(key, 0),
                }

            report_engagement_over_time[platform] = platform_report

        return report_engagement_over_time

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_last_25_posts(self):
        platforms = ["facebook", "linkedin", "instagram"]
        report_latest_posts = {}

        for platform in platforms:
            post_data = self.metadata.get(platform, {}).get("post_data", [])
            report_latest_posts[platform] = {
                f"post{i+1}": {
                    "likes": post.get("engagement_count", 0),
                    "comments": post.get("comment_count", 0),
                }
                for i, post in enumerate(post_data[:25])
            }

        return report_latest_posts

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_audience_location(self):
        platforms = ["facebook", "linkedin", "instagram"]
        report_audience_demographics = {}

        for platform in platforms:
            platform_insights = (
                self.metadata.get(platform, {})
                .get("current_period_insights", {})
                .get("audience_location", {})
            )
            report_audience_demographics[platform] = platform_insights

        return report_audience_demographics

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_most_used_hashtags(self):
        start_date, _ = DateHelper.get_date_range(self.request.period)

        results = {}

        # Loop through each platform in the divided metadata
        for platform, platform_metadata in self.metadata.items():
            posts = platform_metadata.get("post_data", [])

            current_posts = AccountTrackingReportGenHelper.extract_current_period_posts(
                posts, start_date
            )

            # Decide which text key to use
            text_key = (
                "caption"
                if platform.lower() == PostPlatformEnum.INSTAGRAM.value.lower()
                else "content"
            )

            # Compute the hashtag frequency
            most_frequent_hashtags = TextHelper.compute_hashtag_frequency(
                current_posts, text_key, 15
            )

            results[platform] = most_frequent_hashtags

        return results

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_summary_and_achievement(self) -> Optional[SummaryAndAchievement]:
        if not self.report_data:
            print("Report data missing for getting summary & achievements")
            return None
        summary_and_achievements = (
            await ReportGenAiService.generate_summary_and_achievements(self.report_data)
        )
        return SummaryAndAchievement(**summary_and_achievements)

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_activity_overview(self) -> Optional[ActivityOverview]:
        if not self.metadata:
            print("Missing metadata for getting activity overview")
            return None

        # gather post_data from all platforms
        platforms = ["facebook", "linkedin", "instagram"]
        all_posts = []

        for platform in platforms:
            posts = self.metadata.get(platform, {}).get("post_data", [])
            all_posts.extend(posts)

        posts_length = len(all_posts)
        if not posts_length:
            return None

        # compute totals
        total_likes = sum(item.get("engagement_count", 0) for item in all_posts)
        total_comments = sum(item.get("comment_count", 0) for item in all_posts)
        total_impressions = sum(
            (item.get("comment_count", 0) + item.get("engagement_count", 0))
            for item in all_posts
        )

        # compute averages
        activity_overview = {
            "averageLikes": total_likes // posts_length,
            "averageComments": total_comments // posts_length,
            "averageImpressionsPerPost": total_impressions // posts_length,
        }

        activity_overview.update(
            await ReportGenAiService.generate_activity_overview(all_posts)
        )

        return ActivityOverview(**activity_overview)

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_ai_industry_classification(
        self,
    ) -> Optional[AIIndustryClassification]:
        if not self.report_data:
            print("Missing report data fot getting AI industry classification")
            return None
        ai_industry_classification = (
            await ReportGenAiService.generate_ai_industry_classification(
                self.report_data
            )
        )

        return AIIndustryClassification(**ai_industry_classification)

    @AccountTrackingReportGenHelper.cache_result("CACHE_TTL")
    async def get_top_suggested_improvement(self):
        top_improvement_data = (
            await ReportGenAiService.generate_top_suggested_improvement(
                self.report_data
            )
        )

        return top_improvement_data

    async def calculate_performance_metrics(self):
        performance_metrics_by_platform = {}

        for platform, platform_metadata in self.metadata.items():
            post_data = platform_metadata.get("post_data", [{}])

            total_posts_kpi, positive_sentiment_kpi, top_performing_hashtag_kpi = (
                await AccountTrackingReportGenHelper.extract_total_posts_sentiments_and_hashtag_kpi(
                    post_data, self.request.period
                )
            )

            performance_metrics_by_platform[platform] = [
                total_posts_kpi,
                AccountTrackingReportGenHelper.extract_total_engagements_kpi(
                    platform_metadata
                ),
                AccountTrackingReportGenHelper.extract_engagement_rate_kpi(
                    platform_metadata
                ),
                positive_sentiment_kpi,
                AccountTrackingReportGenHelper.extract_followers_growth_kpi(
                    platform_metadata
                ),
                top_performing_hashtag_kpi,
            ]

        return performance_metrics_by_platform
