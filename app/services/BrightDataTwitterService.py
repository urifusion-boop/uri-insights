"""
BrightDataTwitterService - Unified Twitter/X profile enrichment and posts scraping
Uses Bright Data Python SDK Profiles API with max_number_of_posts parameter

This unified service handles both:
1. Profile enrichment (name, bio, followers, verified status, profile image)
2. Posts scraping (recent tweets for buying signal detection)

Uses ONE API endpoint: client.scrape.twitter.profiles() with flexible max_number_of_posts

Replaces: OpenAIApifyTwitterService (Apify-based)
"""
import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class BrightDataTwitterService:
    """
    Unified service for Twitter/X profile enrichment and posts scraping
    Uses: client.scrape.twitter.profiles() - Profiles API with max_number_of_posts
    """

    def __init__(self):
        """Initialize the service with Bright Data client"""
        try:
            from brightdata import BrightDataClient

            if not hasattr(settings, 'BRIGHTDATA_API_TOKEN') or not settings.BRIGHTDATA_API_TOKEN:
                logger.warning("BRIGHTDATA_API_TOKEN not configured. Twitter scraping will not work.")
                self.client = None
            else:
                # Initialize Bright Data client
                self.client = BrightDataClient(token=settings.BRIGHTDATA_API_TOKEN)
                logger.info("✅ BrightData client initialized successfully for Twitter")
        except ImportError:
            logger.error("brightdata-sdk package not installed. Run: pip install brightdata-sdk")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize BrightData client: {str(e)}")
            self.client = None

    async def enrich_profile(
        self,
        twitter_url: str,
        include_posts: bool = False,
        max_posts: int = 0,
        timeout_seconds: int = 90
    ) -> Dict[str, Any]:
        """
        Enrich a Twitter/X profile with profile data and optionally recent posts

        Args:
            twitter_url: Full Twitter/X profile URL (e.g., "https://x.com/username" or "https://twitter.com/username")
            include_posts: Whether to include recent posts (default: False for pure enrichment)
            max_posts: Maximum number of posts to fetch if include_posts=True (default: 0)
            timeout_seconds: Maximum time to wait for scraping (default: 90s)

        Returns:
            Dictionary containing enriched profile data and optional posts:
            {
                "success": True,
                "profile": {
                    "x_id": "123456789",
                    "url": "https://x.com/username",
                    "profile_name": "@username",
                    "biography": "Bio text...",
                    "is_verified": True,
                    "profile_image_link": "https://...",
                    "external_link": "https://website.com",
                    "date_joined": "2010-01-01",
                    "location": "San Francisco, CA",
                    "followers": 10000,
                    "following": 500,
                    "posts_count": 5000,
                    "is_business_account": False,
                    "is_government_account": False,
                    "category_name": "",
                    "scraped_at": "2026-02-13T10:30:00.000Z"
                },
                "posts": [...]  # Only if include_posts=True
            }
        """
        try:
            # Check if client is initialized
            if not self.client:
                return {
                    "success": False,
                    "error_message": "BrightData client not initialized. Please configure BRIGHTDATA_API_TOKEN and install brightdata-sdk.",
                    "profile": {},
                    "posts": []
                }

            # Validate Twitter URL
            if not twitter_url or not ("x.com" in twitter_url or "twitter.com" in twitter_url):
                return {
                    "success": False,
                    "error_message": "Invalid Twitter/X URL. Must contain 'x.com' or 'twitter.com'",
                    "profile": {},
                    "posts": []
                }

            # Determine max_number_of_posts parameter
            max_number_of_posts = max_posts if include_posts else 0

            logger.info(f"🔍 Enriching Twitter profile via Bright Data: {twitter_url} (max_posts={max_number_of_posts})")

            # Fetch profile (and optionally posts) from Bright Data
            profile_result = await self._scrape_profile_from_brightdata(
                twitter_url,
                max_number_of_posts,
                timeout_seconds
            )

            return profile_result

        except Exception as e:
            logger.error(f"Error in enrich_profile: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": f"An error occurred: {str(e)}",
                "profile": {},
                "posts": []
            }

    async def _scrape_profile_from_brightdata(
        self,
        twitter_url: str,
        max_number_of_posts: int,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """
        Scrape Twitter profile using Bright Data SDK Profiles API

        Args:
            twitter_url: Twitter/X profile URL
            max_number_of_posts: Number of recent posts to include (0 = no posts)
            timeout_seconds: Timeout for the request

        Returns:
            Dictionary containing profile data and optional posts
        """
        try:
            # Run Bright Data SDK call in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.scrape.twitter.profiles(
                    url=twitter_url,
                    max_number_of_posts=max_number_of_posts,
                    timeout=timeout_seconds
                )
            )

            # Check if request was successful
            if not result.success:
                error_msg = getattr(result, 'error_message', 'Unknown error from Bright Data')
                logger.error(f"Bright Data request failed: {error_msg}")
                return {
                    "success": False,
                    "error_message": error_msg,
                    "profile": {},
                    "posts": []
                }

            # Extract profile data from result
            if not result.data or len(result.data) == 0:
                logger.warning(f"No profile data returned for: {twitter_url}")
                return {
                    "success": False,
                    "error_message": "No profile data found. Profile may be private or does not exist.",
                    "profile": {},
                    "posts": []
                }

            # Get first profile (should be the only one for single URL)
            raw_profile = result.data[0]

            # Log sample structure for debugging
            logger.debug(f"Bright Data Twitter profile keys: {list(raw_profile.keys())}")

            # Parse and normalize profile data
            profile = self._parse_profile_data(raw_profile)

            # Extract posts if included
            posts = []
            if max_number_of_posts > 0:
                raw_posts = raw_profile.get("posts") or []
                posts = [self._parse_post_data(raw_post) for raw_post in raw_posts]
                logger.info(f"✅ Fetched {len(posts)} posts for {twitter_url}")

            logger.info(f"✅ Successfully enriched Twitter profile: {profile['profile_name']}")

            return {
                "success": True,
                "profile": profile,
                "posts": posts
            }

        except Exception as e:
            logger.error(f"Error scraping profile from Bright Data: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": str(e),
                "profile": {},
                "posts": []
            }

    def _parse_profile_data(self, raw_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and normalize profile data from Bright Data response

        Args:
            raw_profile: Raw profile data from Bright Data

        Returns:
            Normalized profile dictionary
        """
        # Extract profile fields with fallbacks
        x_id = (
            raw_profile.get("x_id") or
            raw_profile.get("id") or
            raw_profile.get("user_id") or
            ""
        )

        url = (
            raw_profile.get("url") or
            raw_profile.get("profile_url") or
            ""
        )

        profile_name = (
            raw_profile.get("profile_name") or
            raw_profile.get("username") or
            raw_profile.get("name") or
            "Unknown"
        )

        biography = (
            raw_profile.get("biography") or
            raw_profile.get("bio") or
            raw_profile.get("description") or
            ""
        )

        is_verified = (
            raw_profile.get("is_verified") or
            raw_profile.get("verified") or
            False
        )

        profile_image_link = (
            raw_profile.get("profile_image_link") or
            raw_profile.get("profile_image") or
            raw_profile.get("avatar") or
            raw_profile.get("photo") or
            ""
        )

        external_link = (
            raw_profile.get("external_link") or
            raw_profile.get("website") or
            raw_profile.get("url_website") or
            ""
        )

        date_joined = (
            raw_profile.get("date_joined") or
            raw_profile.get("created_at") or
            raw_profile.get("joined_date") or
            ""
        )

        location = (
            raw_profile.get("location") or
            raw_profile.get("geo") or
            ""
        )

        followers = (
            raw_profile.get("followers") or
            raw_profile.get("followers_count") or
            0
        )

        following = (
            raw_profile.get("following") or
            raw_profile.get("following_count") or
            0
        )

        posts_count = (
            raw_profile.get("posts_count") or
            raw_profile.get("tweets_count") or
            raw_profile.get("statuses_count") or
            0
        )

        subscriptions = (
            raw_profile.get("subscriptions") or
            0
        )

        birth_date = (
            raw_profile.get("birth_date") or
            raw_profile.get("birthday") or
            ""
        )

        is_business_account = (
            raw_profile.get("is_business_account") or
            False
        )

        is_government_account = (
            raw_profile.get("is_government_account") or
            False
        )

        category_name = (
            raw_profile.get("category_name") or
            raw_profile.get("category") or
            ""
        )

        # Build normalized profile data
        return {
            "x_id": x_id,
            "url": url,
            "profile_name": profile_name,
            "biography": biography,
            "is_verified": is_verified,
            "profile_image_link": profile_image_link,
            "external_link": external_link,
            "date_joined": date_joined,
            "location": location,
            "followers": followers,
            "following": following,
            "subscriptions": subscriptions,
            "posts_count": posts_count,
            "birth_date": birth_date,
            "is_business_account": is_business_account,
            "is_government_account": is_government_account,
            "category_name": category_name,
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }

    def _parse_post_data(self, raw_post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and normalize post data from Bright Data response

        Args:
            raw_post: Raw post data from Bright Data

        Returns:
            Normalized post dictionary
        """
        # Extract post fields with fallbacks
        post_id = (
            raw_post.get("id") or
            raw_post.get("post_id") or
            raw_post.get("tweet_id") or
            ""
        )

        user_posted = (
            raw_post.get("user_posted") or
            raw_post.get("author") or
            raw_post.get("username") or
            ""
        )

        name = (
            raw_post.get("name") or
            raw_post.get("author_name") or
            ""
        )

        description = (
            raw_post.get("description") or
            raw_post.get("text") or
            raw_post.get("content") or
            ""
        )

        date_posted = (
            raw_post.get("date_posted") or
            raw_post.get("created_at") or
            raw_post.get("posted_at") or
            datetime.now(timezone.utc).isoformat()
        )

        url = (
            raw_post.get("url") or
            raw_post.get("post_url") or
            raw_post.get("tweet_url") or
            ""
        )

        replies = (
            raw_post.get("replies") or
            raw_post.get("reply_count") or
            0
        )

        reposts = (
            raw_post.get("reposts") or
            raw_post.get("retweet_count") or
            0
        )

        likes = (
            raw_post.get("likes") or
            raw_post.get("like_count") or
            0
        )

        views = (
            raw_post.get("views") or
            raw_post.get("view_count") or
            0
        )

        quotes = (
            raw_post.get("quotes") or
            raw_post.get("quote_count") or
            0
        )

        bookmarks = (
            raw_post.get("bookmarks") or
            raw_post.get("bookmark_count") or
            0
        )

        hashtags = (
            raw_post.get("hashtags") or
            []
        )

        tagged_users = (
            raw_post.get("tagged_users") or
            []
        )

        external_url = (
            raw_post.get("external_url") or
            ""
        )

        external_image_urls = (
            raw_post.get("external_image_urls") or
            []
        )

        videos = (
            raw_post.get("videos") or
            []
        )

        # Build normalized post data
        return {
            "id": post_id,
            "user_posted": user_posted,
            "name": name,
            "text": description,  # Map 'description' to 'text' for consistency with LinkedIn
            "description": description,
            "date_posted": date_posted,
            "created_at": date_posted,  # Alias for consistency
            "url": url,
            "replies": replies,
            "comments": replies,  # Alias for consistency with LinkedIn
            "reposts": reposts,
            "likes": likes,
            "views": views,
            "quotes": quotes,
            "bookmarks": bookmarks,
            "hashtags": hashtags,
            "tagged_users": tagged_users,
            "external_url": external_url,
            "external_image_urls": external_image_urls,
            "videos": videos,
            "source": "Twitter",
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }

    async def fetch_posts_realtime(
        self,
        twitter_url: str,
        limit: int = 10,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Fetch recent posts for a single Twitter profile in real-time (for "Scan Now" button)

        This fetches the profile + recent posts in one API call using Profiles API.

        Args:
            twitter_url: Single Twitter/X profile URL
            limit: Maximum number of posts (default: 10)
            timeout_seconds: Timeout for request (default: 60s)

        Returns:
            Dictionary with success status and posts list
        """
        result = await self.enrich_profile(
            twitter_url=twitter_url,
            include_posts=True,
            max_posts=limit,
            timeout_seconds=timeout_seconds
        )

        # Return posts in a simplified format
        if result["success"]:
            return {
                "success": True,
                "posts": result["posts"],
                "total_posts": len(result["posts"]),
                "profile": result["profile"]
            }
        else:
            return {
                "success": False,
                "error_message": result["error_message"],
                "posts": [],
                "profile": {}
            }

    async def fetch_posts_batch(
        self,
        twitter_urls: List[str],
        limit_per_profile: int = 10,
        timeout_seconds: int = 180
    ) -> Dict[str, Any]:
        """
        Fetch posts for multiple Twitter profiles in batch (for Origami weekly scans)

        Args:
            twitter_urls: List of Twitter/X profile URLs
            limit_per_profile: Posts per profile (default: 10)
            timeout_seconds: Timeout per profile (default: 180s)

        Returns:
            Dictionary with posts_by_url and all_posts
        """
        try:
            if not self.client:
                return {
                    "success": False,
                    "error_message": "BrightData client not initialized",
                    "posts_by_url": {},
                    "all_posts": []
                }

            if not twitter_urls:
                return {
                    "success": False,
                    "error_message": "No Twitter URLs provided",
                    "posts_by_url": {},
                    "all_posts": []
                }

            # Filter valid Twitter URLs
            valid_urls = [
                url for url in twitter_urls
                if url and ("x.com" in url or "twitter.com" in url)
            ]

            if not valid_urls:
                return {
                    "success": False,
                    "error_message": "No valid Twitter URLs found",
                    "posts_by_url": {},
                    "all_posts": []
                }

            logger.info(f"🔍 Batch fetching posts from {len(valid_urls)} Twitter profiles via Bright Data")

            # Process URLs concurrently
            tasks = [
                self.fetch_posts_realtime(
                    twitter_url=url,
                    limit=limit_per_profile,
                    timeout_seconds=timeout_seconds
                )
                for url in valid_urls
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            posts_by_url = {}
            all_posts = []

            for url, result in zip(valid_urls, results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching posts for {url}: {str(result)}")
                    posts_by_url[url] = []
                elif result["success"]:
                    posts = result["posts"]
                    posts_by_url[url] = posts
                    all_posts.extend(posts)
                    logger.info(f"✅ Fetched {len(posts)} posts from {url}")
                else:
                    logger.warning(f"⚠️  No posts fetched for {url}: {result.get('error_message')}")
                    posts_by_url[url] = []

            logger.info(f"✅ Successfully fetched {len(all_posts)} total Twitter posts from {len(valid_urls)} profiles")

            return {
                "success": True,
                "total_posts": len(all_posts),
                "posts_by_url": posts_by_url,
                "all_posts": all_posts
            }

        except Exception as e:
            logger.error(f"Error in fetch_posts_batch: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": f"Batch processing error: {str(e)}",
                "posts_by_url": {},
                "all_posts": []
            }

    async def batch_enrich_profiles(
        self,
        twitter_urls: List[str],
        include_posts: bool = False,
        max_posts: int = 0,
        timeout_seconds: int = 180
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich multiple Twitter profiles in batch

        Args:
            twitter_urls: List of Twitter/X profile URLs
            include_posts: Whether to include posts for each profile
            max_posts: Max posts per profile if include_posts=True
            timeout_seconds: Timeout per profile

        Returns:
            Dictionary mapping URL to enriched profile data
        """
        try:
            if not twitter_urls:
                return {}

            logger.info(f"🔍 Batch enriching {len(twitter_urls)} Twitter profiles")

            # Process URLs concurrently
            tasks = [
                self.enrich_profile(
                    twitter_url=url,
                    include_posts=include_posts,
                    max_posts=max_posts,
                    timeout_seconds=timeout_seconds
                )
                for url in twitter_urls
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Map results to URLs
            enriched_profiles = {}
            for url, result in zip(twitter_urls, results):
                if isinstance(result, Exception):
                    logger.error(f"Error enriching {url}: {str(result)}")
                    enriched_profiles[url] = {
                        "success": False,
                        "error_message": str(result),
                        "profile": {},
                        "posts": []
                    }
                else:
                    enriched_profiles[url] = result
                    if result["success"]:
                        logger.info(f"✅ Enriched: {result['profile']['profile_name']}")

            logger.info(f"✅ Batch enrichment completed: {len(enriched_profiles)} profiles processed")
            return enriched_profiles

        except Exception as e:
            logger.error(f"Error in batch_enrich_profiles: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
