from datetime import datetime, timedelta
from enum import Enum
import functools
import inspect
import json
from typing import Any, Callable, Dict, List, Optional

from app.core.helpers.cache_helper import CacheHelper
from app.core.helpers.date_helper import DateHelper
from app.domain.enums.reportgeneration_enum import (
    AccountTrackingKpiName,
    ReportGenSectionKeyEnum,
)
from app.domain.requests.reportgeneration_requests import ReportGenerationRequest
from app.repository.CacheRepository import CacheRepository
from app.repository.InfluencerRepository import InfluencerRepository


class ReportGenerationHelper:
    section_name_to_attribute_map = {
        ReportGenSectionKeyEnum.ENGAGEMENT_OVER_TIME.value: "engagementOverTime",
        ReportGenSectionKeyEnum.LAST_25_POSTS.value: "last25posts",
        ReportGenSectionKeyEnum.AUDIENCE_LOCATION.value: "audienceLocation",
        ReportGenSectionKeyEnum.MOST_USED_HASHTAGS.value: "mostUsedHashtags",
        ReportGenSectionKeyEnum.SUMMARY_AND_ACHIEVEMENT.value: "summaryAndAchievement",
        ReportGenSectionKeyEnum.ACTIVITY_OVERVIEW.value: "activityOverview",
        ReportGenSectionKeyEnum.AI_INDUSTRY_CLASSIFICATION.value: "aiIndustryClassification",
        ReportGenSectionKeyEnum.TOP_SUGGESTED_IMPROVEMENT.value: "topSuggestedImprovement",
        ReportGenSectionKeyEnum.ENGAGEMENTS_AND_LIKES.value: "engagementMetrics",
        ReportGenSectionKeyEnum.RECENT_POSTS.value: "recentPosts",
        ReportGenSectionKeyEnum.POST_TYPE_DISTRIBUTION.value: "postTypeDistribution",
        ReportGenSectionKeyEnum.TRENDING_HASHTAGS.value: "trendingHashtags",
        ReportGenSectionKeyEnum.SENTIMENT_ANALYSIS.value: "sentimentAnalysis",
        ReportGenSectionKeyEnum.HASHTAG_MENTIONS.value: "hashtagMentions",
        ReportGenSectionKeyEnum.RELATED_HASHTAGS.value: "relatedHashtags",
        ReportGenSectionKeyEnum.RECOMMENDATIONS.value: "recommendations",
    }

    @classmethod
    def cache_result(
        cls,
        ttl_attr: str,
        res_attr: Optional[str] = None,
        custom_key_func: Optional[Callable] = None,
    ):
        """
        Class method decorator to cache the result of an asynchronous instance method.

        The decorated method's result is cached using a generated cache key that combines
        the method name and the instance's `cache_key` attribute. On subsequent calls, if
        a cached value exists and is valid, the cached result is returned directly,
        avoiding recomputation.

        Args:
            ttl_attr (str): The name of the instance attribute that holds the cache time-to-live (TTL)
                            duration in hours. This value is used to set how long the cache remains valid.
            res_attr (Optional[str], optional): The name of the instance attribute where the cached or
                            computed result should be stored. If provided, the result will be assigned
                            to this attribute on the instance. Defaults to None.
            custom_key_func (Optional[Callable], optional): A function to get the custom cache key for a specific function if need be.
                            If provided it will be appended to the original cache key and used for that specific
                            function alone. Enabling extremely granular caching logic
        """

        def decorator(fn):
            @functools.wraps(fn)
            async def wrapper(self, *args, **kwargs) -> Any:
                section_key = (
                    f"{fn.__name__}_{self.cache_key}_{custom_key_func(self)}"
                    if custom_key_func
                    else f"{fn.__name__}_{self.cache_key}"
                )
                cache_key = CacheHelper.generate_cache_key(section_key)
                cached = await CacheRepository.get_cache(self.db, cache_key)
                if cached:
                    result = ReportGenerationHelper._reconstruct_from_cache(fn, cached)
                    if res_attr:
                        setattr(self, res_attr, result)
                    print(
                        f"\n\n---------------------- {fn.__name__} RESULT -----------------------"
                    )
                    print(result)
                    print(
                        "------------------------------------------------------------\n\n"
                    )
                    return result
                result = await fn(self, *args, **kwargs)
                to_store = ReportGenerationHelper._unwrap_result(result)
                ttl = timedelta(hours=getattr(self, ttl_attr))
                await CacheRepository.set_cache(self.db, cache_key, to_store, ttl)
                print(
                    f"\n\n---------------------- {fn.__name__} RESULT -----------------------"
                )
                print(result)
                print(
                    "------------------------------------------------------------\n\n"
                )
                return result

            return wrapper

        return decorator

    @staticmethod
    def _reconstruct_from_cache(fn, cached_data: dict) -> Any:
        """
        If the decorated function’s declared return type is a Pydantic model,
        instantiate it with the cached dict; otherwise return the raw dict.
        """
        return_type = fn.__annotations__.get("return")
        if (
            return_type
            and inspect.isclass(return_type)
            and hasattr(return_type, "parse_obj")
        ):
            # Pydantic models support parse_obj / instantiate via **kwargs
            return return_type(**cached_data)
        return cached_data

    @staticmethod
    def _unwrap_result(result: Any) -> Any:
        """
        If the result is a Pydantic model, convert to dict; otherwise assume
        it’s a primitive or dict already.
        """
        if hasattr(result, "dict"):
            # exclude None so cache stays minimal
            return result.dict(exclude_none=True)
        return result

    @staticmethod
    def __calculate_percentage_change(current, previous):
        try:
            previous = float(previous)
            current = float(current)
            if previous == 0:
                result = "Nil"
                return result
            change = ((current - previous) / abs(previous)) * 100
            change_int = round(change, 2)
            if change_int <= 0:
                return f"{change_int}%"
            return f"+{change_int}%"
        except (ValueError, TypeError):
            return None

    @staticmethod
    def construct_kpi_dict(kpi_name, current, previous) -> Optional[dict]:
        try:
            result = {
                "kpi": kpi_name,
                "currentPeriod": current,
                "previousPeriod": previous,
                "change": (
                    "-"
                    if kpi_name == AccountTrackingKpiName.TOP_PERFORMING_HASHTAG.value
                    or kpi_name == "Top Post Type"
                    else ReportGenerationHelper.__calculate_percentage_change(
                        current, previous
                    )
                ),
            }
            return result
        except Exception as e:
            print("Exception in construct KPI dict: ", e)
            raise

    @staticmethod
    def calculate_date_range(period):
        # Calculate the start and end date based on the period
        start_date, end_date = DateHelper.get_date_range(period)

        # Calculate period length and the previous start date
        period_length_days = (end_date - start_date).days
        previous_start = start_date - timedelta(days=period_length_days)

        return start_date, end_date, previous_start

    @staticmethod
    async def get_influencer_data(db, influencer_id, user_id):
        # Retrieve influencer data (token and social_id)
        influencer_data = (
            await InfluencerRepository.get_influencer_specific_data_by_influencer_id(
                db,
                influencer_id,
                ["token", "social_user_id", "user_id", "social_username"],
            )
        )
        if not influencer_data:
            raise ValueError(
                "Influencer data not found. Confirm influencer account has been created."
            )

        if user_id != influencer_data.get("user_id", ""):
            raise ValueError(
                "This user is not authorized to access the info for this influencer account"
            )

        # Extract token and social_id
        token = influencer_data.get("token", "")
        social_id = influencer_data.get("social_user_id", "")
        username = influencer_data.get("social_username", "")

        return token, social_id, username

    @staticmethod
    def transform_report_gen_request_to_string(data: ReportGenerationRequest) -> str:
        data_dict = data.dict()
        del data_dict["account_tracking_included_fields"]
        for key, value in data_dict.items():
            if isinstance(value, Enum):
                data_dict[key] = value.value

        return json.dumps(data_dict)

    @staticmethod
    def normalize_metadata_datetime_formats(data: dict) -> dict:
        normalized_dict = {}
        for key in data:
            if key != "audience_location":
                transformed_insight_metric = {}
                insight_metric = data.get(key, {})
                for inner_key, value in insight_metric.items():
                    normalized_datetime = DateHelper.to_readable_human_format(inner_key)
                    transformed_insight_metric[normalized_datetime] = value
                normalized_dict[key] = transformed_insight_metric
        return normalized_dict

    @staticmethod
    def get_period_insights(metadata: dict):
        current = metadata.get("current_period_insights")
        previous = metadata.get("previous_period_insights")
        if not current or not previous:
            raise ValueError(
                "Current or previous period insights not found for followers growth KPI generation"
            )
        return current, previous

    @staticmethod
    def extract_current_period_posts(
        posts: List[Dict], split_date: datetime, time_key: Optional[str] = "post_time"
    ) -> List[Dict]:
        """
        Returns all posts made **after or on** the split_date.
        """
        # NEEDS TO BE REFACTORD TO BE TIMEZONE AWARE
        result = [
            post
            for post in posts
            if datetime.fromisoformat(post[time_key]).replace(tzinfo=None) >= split_date
        ]
        return result

    @staticmethod
    def extract_previous_period_posts(
        posts: List[Dict],
        split_date: datetime,
        limit_date: datetime,
        time_key: Optional[str] = "post_time",
    ) -> List[Dict]:
        """
        Returns all posts made **before** the split_date and after the limit_date.
        """
        # NEEDS TO BE REFACTORD TO BE TIMEZONE AWARE
        result = [
            post
            for post in posts
            if datetime.fromisoformat(post[time_key]).replace(tzinfo=None) < split_date
            and datetime.fromisoformat(post[time_key]).replace(tzinfo=None)
            >= limit_date
        ]
        return result
