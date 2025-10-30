from typing import Dict, Any
from app.domain.schemas.browsercloud_schema import BrowsercloudPlatformEnum


class BrowsercloudPlatformConfig:
    """Configuration for different social media platforms in Browsercloud."""

    @staticmethod
    def get_platform_config(platform: BrowsercloudPlatformEnum) -> Dict[str, Any]:
        """Get platform-specific configuration."""
        PLATFORM_CONFIGS = {
            BrowsercloudPlatformEnum.TWITTER: {
                "max_results_per_search": 100,
                "rate_limit_per_minute": 60,
                "content_types": ["tweets", "replies"],
                "filters": {
                    "min_followers": 100,
                    "exclude_retweets": True,
                    "exclude_replies": False,
                    "language": "en"
                },
                "engagement_metrics": ["likes", "retweets", "replies", "quotes"]
            },
            BrowsercloudPlatformEnum.LINKEDIN: {
                "max_results_per_search": 50,
                "rate_limit_per_minute": 30,
                "content_types": ["posts", "comments"],
                "filters": {
                    "network_level": "2nd",
                    "post_types": ["text", "article", "event", "poll"],
                    "language": "en"
                },
                "engagement_metrics": ["likes", "comments", "shares", "views"]
            },
            BrowsercloudPlatformEnum.FACEBOOK: {
                "max_results_per_search": 100,
                "rate_limit_per_minute": 40,
                "content_types": ["posts", "comments", "groups"],
                "filters": {
                    "post_type": ["text", "link", "status"],
                    "visibility": "public",
                    "language": "en"
                },
                "engagement_metrics": ["likes", "comments", "shares"]
            },
            BrowsercloudPlatformEnum.THREADS: {
                "max_results_per_search": 50,
                "rate_limit_per_minute": 30,
                "content_types": ["threads", "replies"],
                "filters": {
                    "min_likes": 5,
                    "exclude_replies": False,
                    "language": "en"
                },
                "engagement_metrics": ["likes", "replies", "reposts"]
            }
        }
        
        return PLATFORM_CONFIGS.get(platform, {})

    @staticmethod
    def get_platform_specific_query(
        platform: BrowsercloudPlatformEnum,
        keywords: list[str],
        buying_signals: list[str],
        excluded_keywords: list[str] = None,
        location: str = None
    ) -> Dict[str, Any]:
        """Build platform-specific search query."""
        base_query = {
            "keywords": keywords,
            "buying_signals": buying_signals,
            "excluded_keywords": excluded_keywords or [],
            "location": location,
            **BrowsercloudPlatformConfig.get_platform_config(platform)
        }

        # Platform-specific query modifications
        if platform == BrowsercloudPlatformEnum.TWITTER:
            base_query.update({
                "search_type": "advanced",
                "result_type": "recent",
                "tweet_mode": "extended"
            })
        elif platform == BrowsercloudPlatformEnum.LINKEDIN:
            base_query.update({
                "search_scope": "posts",
                "time_range": "past_24h",
                "sort_by": "recent"
            })
        elif platform == BrowsercloudPlatformEnum.FACEBOOK:
            base_query.update({
                "search_type": "posts",
                "time_range": "24h",
                "include_groups": True
            })
        elif platform == BrowsercloudPlatformEnum.THREADS:
            base_query.update({
                "search_type": "keyword",
                "sort_by": "recent",
                "include_replies": True
            })

        return base_query

    @staticmethod
    def get_rate_limit_config() -> Dict[str, Any]:
        """Get rate limiting configuration for Browsercloud API."""
        return {
            "max_requests_per_minute": 120,
            "max_concurrent_tasks": 10,
            "retry_after": 60,  # seconds
            "max_retries": 3
        }

    @staticmethod
    def get_webhook_config() -> Dict[str, Any]:
        """Get webhook configuration."""
        return {
            "max_payload_size": 5 * 1024 * 1024,  # 5MB
            "timeout": 30,  # seconds
            "retry_count": 3,
            "retry_delay": 5  # seconds
        }