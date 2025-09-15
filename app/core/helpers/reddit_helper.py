from datetime import datetime
from typing import Any, Dict, Optional
from app.core.config import settings
from app.domain.enums.reddit_enum import RedditSearchSortEnum, RedditSearchTEnum
from app.domain.requests.reddit_requests import RedditSearchParams


class RedditHelper:
    @staticmethod
    def generate_user_agent():
        reddit_app_name = settings.REDDIT_APP_NAME
        reddit_app_version = settings.REDDIT_APP_VERSION
        reddit_username = settings.REDDIT_USERNAME

        if reddit_username and reddit_app_version and reddit_username:
            return f"server:{reddit_app_name}:{reddit_app_version} (by /u/f{reddit_username})"

    @staticmethod
    def construct_reddit_search_params_from_business_info(
        business_info: dict,
    ) -> Dict[str, Any]:
        """
        Construct RedditSearchParams from business information.
        """
        params_dict = {
            "q": " OR ".join(business_info.get("keywords", [])),
            "sort": RedditSearchSortEnum.NEW,
            "t": RedditHelper.__get_t_from_business_info(
                business_info.get("settings", {}).get("last_scraped_date")
            ),
            "max_pages": 1,
        }
        result = {
            "user_id": business_info.get("user_id"),
            "params": RedditSearchParams(**params_dict),
            "platform": "reddit",
        }
        return result

    @staticmethod
    def __get_t_from_business_info(
        last_scraped_date: Optional[datetime],
    ) -> RedditSearchTEnum:
        """
        Get t from business information.
        """
        if not last_scraped_date:
            return RedditSearchTEnum.ALL
        time_difference = (datetime.utcnow() - last_scraped_date).days
        print(f"Time difference: {time_difference}")
        if time_difference < 0:
            return RedditSearchTEnum.ALL  # Future dates: fallback
        if time_difference < 1:
            return RedditSearchTEnum.HOUR
        if time_difference < 7:
            return RedditSearchTEnum.DAY
        if time_difference < 30:
            return RedditSearchTEnum.WEEK
        if time_difference < 365:
            return RedditSearchTEnum.MONTH
        return RedditSearchTEnum.ALL
