"""
BrightDataLinkedInPostsService - Scrapes LinkedIn posts for Lazarus Protocol monitoring
Uses Bright Data Python SDK Web Scraper API (client.search.linkedin.posts)

This service fetches LinkedIn posts from user profiles for:
1. Real-time "Scan Now" functionality (manual trigger)
2. Weekly background scans via Origami Method (batch processing)
3. Buying signal detection and job change monitoring

Replaces: ApifyLinkedInPostScraperService (Apify-based)
"""
import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timezone, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class BrightDataLinkedInPostsService:
    """
    Service to scrape LinkedIn posts using Bright Data Python SDK
    Uses: client.search.linkedin.posts() - Web Scraper API
    """

    def __init__(self):
        """Initialize the service with Bright Data API token"""
        try:
            from brightdata import BrightDataClient

            if not hasattr(settings, 'BRIGHTDATA_API_TOKEN') or not settings.BRIGHTDATA_API_TOKEN:
                logger.warning("BRIGHTDATA_API_TOKEN not configured. LinkedIn posts scraping will not work.")
                self.api_token = None
                self.BrightDataClient = None
            else:
                # Store API token and client class for async context manager usage
                self.api_token = settings.BRIGHTDATA_API_TOKEN
                self.BrightDataClient = BrightDataClient
                logger.info("✅ BrightData API token configured successfully for LinkedIn posts")
        except ImportError:
            logger.error("brightdata-sdk package not installed. Run: pip install brightdata-sdk")
            self.api_token = None
            self.BrightDataClient = None
        except Exception as e:
            logger.error(f"Failed to initialize BrightData: {str(e)}")
            self.api_token = None
            self.BrightDataClient = None

    async def fetch_linkedin_posts(
        self,
        linkedin_urls: List[str],
        limit_per_source: int = 10,
        days_back: int = 90,
        timeout_seconds: int = 120
    ) -> Dict[str, Any]:
        """
        Fetch LinkedIn posts from user profiles using Bright Data Web Scraper API

        Args:
            linkedin_urls: List of LinkedIn profile URLs to scrape
            limit_per_source: Maximum number of posts to fetch per URL (default: 10)
            days_back: How many days back to fetch posts (default: 90 days)
            timeout_seconds: Timeout for the entire batch request (default: 120s)

        Returns:
            Dictionary containing posts and metadata:
            {
                "success": True,
                "total_posts": 25,
                "posts_by_url": {
                    "https://linkedin.com/in/user1": [
                        {
                            "text": "Post content...",
                            "url": "https://linkedin.com/posts/...",
                            "created_at": "2025-01-15T10:00:00Z",
                            "author": "User Name",
                            "author_url": "https://linkedin.com/in/user1",
                            "likes": 42,
                            "comments": 5,
                            "shares": 3,
                            "hashtags": ["AI", "Tech"],
                            "source": "LinkedIn"
                        }
                    ]
                },
                "all_posts": [...]  # Flattened list of all posts
            }
        """
        try:
            # Check if client is initialized
            if not self.BrightDataClient or not self.api_token:
                return {
                    "success": False,
                    "error_message": "BrightData client not initialized. Please configure BRIGHTDATA_API_TOKEN and install brightdata-sdk.",
                    "posts_by_url": {},
                    "all_posts": []
                }

            # Validate inputs
            if not linkedin_urls:
                return {
                    "success": False,
                    "error_message": "No LinkedIn URLs provided",
                    "posts_by_url": {},
                    "all_posts": []
                }

            # Filter and validate LinkedIn URLs (must be profile URLs)
            valid_urls = []
            for url in linkedin_urls:
                if url and "linkedin.com/in/" in url:
                    valid_urls.append(url)
                else:
                    logger.warning(f"Skipping invalid LinkedIn profile URL: {url}")

            if not valid_urls:
                return {
                    "success": False,
                    "error_message": "No valid LinkedIn profile URLs found. URLs must contain 'linkedin.com/in/'",
                    "posts_by_url": {},
                    "all_posts": []
                }

            logger.info(f"🔍 Fetching LinkedIn posts from {len(valid_urls)} profiles via Bright Data")

            # Calculate date range for posts
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)

            # Fetch posts for each URL
            posts_by_url = {}
            all_posts = []

            # Process URLs concurrently for better performance
            tasks = [
                self._fetch_posts_for_profile(
                    profile_url=url,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit_per_source,
                    timeout_seconds=timeout_seconds
                )
                for url in valid_urls
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
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

            logger.info(f"✅ Successfully fetched {len(all_posts)} total LinkedIn posts from {len(valid_urls)} profiles")

            return {
                "success": True,
                "total_posts": len(all_posts),
                "posts_by_url": posts_by_url,
                "all_posts": all_posts
            }

        except Exception as e:
            logger.error(f"Error in fetch_linkedin_posts: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": f"An error occurred: {str(e)}",
                "posts_by_url": {},
                "all_posts": []
            }

    async def _fetch_posts_for_profile(
        self,
        profile_url: str,
        start_date: datetime,
        end_date: datetime,
        limit: int,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """
        Fetch posts for a single LinkedIn profile using Bright Data SDK

        Args:
            profile_url: LinkedIn profile URL
            start_date: Start date for post filtering
            end_date: End date for post filtering
            limit: Maximum number of posts to fetch
            timeout_seconds: Timeout for the request

        Returns:
            Dictionary with success status and posts list
        """
        try:
            logger.info(f"🔍 Fetching posts for profile: {profile_url}")

            # Format dates as strings (YYYY-MM-DD)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

            # Use Bright Data client as async context manager
            # NOTE: SDK uses async dataset mode which takes 30-60s to build
            # We need a much longer timeout to allow dataset building + polling
            async with self.BrightDataClient(token=self.api_token) as client:
                # Pass profile URL as positional argument (SDK doesn't accept named params)
                result = await client.search.linkedin.posts(
                    profile_url,  # Positional argument
                    timeout=max(timeout_seconds, 600)  # Minimum 10 minutes for dataset building
                )

            # Check if request was successful
            if not result.success:
                error_msg = getattr(result, 'error_message', 'Unknown error from Bright Data')
                logger.error(f"Bright Data request failed for {profile_url}: {error_msg}")
                # Debug: Log full result details
                logger.error(f"Full result object: success={result.success}, hasattr error_message={hasattr(result, 'error_message')}")
                logger.error(f"Result dir: {[attr for attr in dir(result) if not attr.startswith('_')]}")
                if hasattr(result, 'errors'):
                    logger.error(f"Result errors: {result.errors}")
                if hasattr(result, 'error'):
                    logger.error(f"Result error: {result.error}")
                return {
                    "success": False,
                    "error_message": error_msg,
                    "posts": []
                }

            # Extract posts from result
            if not result.data or len(result.data) == 0:
                logger.info(f"No posts found for {profile_url} in date range {start_date_str} to {end_date_str}")
                return {
                    "success": True,
                    "posts": []
                }

            # Limit posts to the specified number
            raw_posts = result.data[:limit]

            # Parse and normalize posts
            posts = [self._parse_post_data(raw_post, profile_url) for raw_post in raw_posts]

            logger.info(f"✅ Fetched {len(posts)} posts for {profile_url}")

            return {
                "success": True,
                "posts": posts
            }

        except Exception as e:
            logger.error(f"Error fetching posts for {profile_url}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": str(e),
                "posts": []
            }

    def _parse_post_data(self, raw_post: Dict[str, Any], profile_url: str) -> Dict[str, Any]:
        """
        Parse and normalize post data from Bright Data response
        Handles field name variations and extracts structured data

        Args:
            raw_post: Raw post data from Bright Data
            profile_url: LinkedIn profile URL (for author_url fallback)

        Returns:
            Normalized post dictionary
        """
        # Extract text content
        text = (
            raw_post.get("text") or
            raw_post.get("content") or
            raw_post.get("postText") or
            raw_post.get("description") or
            ""
        )

        # Extract post URL
        url = (
            raw_post.get("url") or
            raw_post.get("postUrl") or
            raw_post.get("link") or
            raw_post.get("permalink") or
            ""
        )

        # Extract creation date/time
        created_at = (
            raw_post.get("created_at") or
            raw_post.get("createdAt") or
            raw_post.get("postedDate") or
            raw_post.get("publishedAt") or
            raw_post.get("date") or
            datetime.now(timezone.utc).isoformat()
        )

        # Normalize date to ISO format
        created_at = self._normalize_date(created_at)

        # Extract author information
        author = (
            raw_post.get("author") or
            raw_post.get("authorName") or
            raw_post.get("creator") or
            raw_post.get("name") or
            "Unknown"
        )

        author_url = (
            raw_post.get("author_url") or
            raw_post.get("authorUrl") or
            raw_post.get("authorProfileUrl") or
            raw_post.get("profileUrl") or
            profile_url  # Fallback to input profile URL
        )

        # Extract engagement metrics
        likes = (
            raw_post.get("likes") or
            raw_post.get("numLikes") or
            raw_post.get("likeCount") or
            raw_post.get("num_likes") or
            0
        )

        comments = (
            raw_post.get("comments") or
            raw_post.get("numComments") or
            raw_post.get("commentCount") or
            raw_post.get("num_comments") or
            0
        )

        shares = (
            raw_post.get("shares") or
            raw_post.get("numShares") or
            raw_post.get("shareCount") or
            raw_post.get("num_shares") or
            0
        )

        # Extract hashtags
        hashtags = (
            raw_post.get("hashtags") or
            raw_post.get("tags") or
            []
        )

        # Ensure hashtags is a list
        if isinstance(hashtags, str):
            # Parse hashtags from text if it's a string
            hashtags = [tag.strip() for tag in hashtags.split(",") if tag.strip()]

        # Extract title (for articles)
        title = (
            raw_post.get("title") or
            raw_post.get("headline") or
            ""
        )

        # Build normalized post data
        return {
            "text": text,
            "url": url,
            "created_at": created_at,
            "author": author,
            "author_url": author_url,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "hashtags": hashtags,
            "title": title,
            "source": "LinkedIn",
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }

    def _normalize_date(self, date_value: Any) -> str:
        """
        Normalize date to ISO format string

        Args:
            date_value: Date in various formats (string, datetime, timestamp)

        Returns:
            ISO formatted date string
        """
        if not date_value:
            return datetime.now(timezone.utc).isoformat()

        try:
            # If already a string in ISO format
            if isinstance(date_value, str):
                if "T" in date_value:
                    return date_value  # Already ISO format
                # Try parsing common formats
                from dateutil import parser
                parsed_date = parser.parse(date_value)
                return parsed_date.isoformat()

            # If datetime object
            if isinstance(date_value, datetime):
                return date_value.isoformat()

            # If timestamp
            if isinstance(date_value, (int, float)):
                return datetime.fromtimestamp(date_value, tz=timezone.utc).isoformat()

            # Fallback
            return str(date_value)

        except Exception as e:
            logger.warning(f"Could not parse date '{date_value}': {str(e)}")
            return datetime.now(timezone.utc).isoformat()

    async def fetch_posts_realtime(
        self,
        linkedin_url: str,
        limit: int = 10,
        days_back: int = 90,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Fetch posts for a single profile in real-time (for "Scan Now" button)

        This is a convenience wrapper around fetch_linkedin_posts() for single URL usage.

        Args:
            linkedin_url: Single LinkedIn profile URL
            limit: Maximum number of posts (default: 10)
            days_back: How many days back to fetch (default: 90)
            timeout_seconds: Timeout for request (default: 60s)

        Returns:
            Dictionary with success status and posts list
        """
        result = await self.fetch_linkedin_posts(
            linkedin_urls=[linkedin_url],
            limit_per_source=limit,
            days_back=days_back,
            timeout_seconds=timeout_seconds
        )

        # Extract posts for this specific URL
        if result["success"]:
            posts = result["posts_by_url"].get(linkedin_url, [])
            return {
                "success": True,
                "posts": posts,
                "total_posts": len(posts)
            }
        else:
            return {
                "success": False,
                "error_message": result["error_message"],
                "posts": []
            }

    async def fetch_posts_batch(
        self,
        linkedin_urls: List[str],
        limit_per_source: int = 10,
        days_back: int = 7,
        timeout_seconds: int = 180
    ) -> Dict[str, Any]:
        """
        Fetch posts for multiple profiles in batch (for Origami weekly scans)

        This is an alias of fetch_linkedin_posts() with batch-optimized defaults.

        Args:
            linkedin_urls: List of LinkedIn profile URLs
            limit_per_source: Posts per profile (default: 10)
            days_back: Days back to scan (default: 7 for weekly scans)
            timeout_seconds: Timeout (default: 180s for batch)

        Returns:
            Dictionary with posts_by_url and all_posts
        """
        return await self.fetch_linkedin_posts(
            linkedin_urls=linkedin_urls,
            limit_per_source=limit_per_source,
            days_back=days_back,
            timeout_seconds=timeout_seconds
        )
