"""
BrightDataLinkedInPostsService - Scrapes LinkedIn posts for Lazarus Protocol monitoring
Uses Bright Data REST API with async polling

This service fetches LinkedIn posts from user profiles for:
1. Real-time "Scan Now" functionality (manual trigger)
2. Weekly background scans via Origami Method (batch processing)
3. Buying signal detection and job change monitoring

Replaces: ApifyLinkedInPostScraperService (Apify-based)
"""
import asyncio
import httpx
import json
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
        if not hasattr(settings, 'BRIGHTDATA_API_TOKEN') or not settings.BRIGHTDATA_API_TOKEN:
            logger.warning("BRIGHTDATA_API_TOKEN not configured. LinkedIn posts scraping will not work.")
            self.api_token = None
        else:
            self.api_token = settings.BRIGHTDATA_API_TOKEN
            logger.info("✅ BrightData API token configured successfully for LinkedIn posts")

        # Dataset ID for LinkedIn Posts - Discover by Profile URL
        self.dataset_id = "gd_lyy3tktm25m4avu764"
        self.base_url = "https://api.brightdata.com"

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
            # Check if API token is configured
            if not self.api_token:
                return {
                    "success": False,
                    "error_message": "BrightData API token not configured. Please set BRIGHTDATA_API_TOKEN.",
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
        Fetch posts for a single LinkedIn profile using Bright Data REST API.
        Returns posts immediately in JSONL format (no polling needed).

        Args:
            profile_url: LinkedIn profile URL
            start_date: Start date for post filtering (NOT USED - dates unreliable in LinkedIn data)
            end_date: End date for post filtering (NOT USED - dates unreliable in LinkedIn data)
            limit: Maximum number of posts to fetch
            timeout_seconds: Maximum time to wait for scraping job to complete

        Returns:
            Dictionary with success status and posts list
        """
        try:
            if not self.api_token:
                return {
                    "success": False,
                    "error_message": "BrightData API token not configured",
                    "posts": []
                }

            logger.info(f"🔍 Fetching LinkedIn posts for: {profile_url}")

            # Fetch posts directly (API returns JSONL immediately)
            raw_posts = await self._trigger_and_fetch_posts(profile_url, timeout_seconds)
            if raw_posts is None:
                return {
                    "success": False,
                    "error_message": "Failed to fetch posts from Bright Data",
                    "posts": []
                }

            # Parse and normalize posts (includes reshares and feed posts)
            posts = [self._parse_post_data(raw_post, profile_url) for raw_post in raw_posts[:limit]]

            logger.info(f"✅ Fetched {len(posts)} LinkedIn posts for {profile_url}")

            # Log posts for visibility
            print(f"\n📝 FETCHED {len(posts)} LINKEDIN POSTS:")
            for i, post in enumerate(posts[:5], 1):  # Show first 5 posts
                print(f"\n   Post {i}:")
                print(f"   Author: {post.get('author', 'Unknown')}")
                print(f"   Text: {post.get('text', 'No text')[:150]}...")
                print(f"   Date: {post.get('created_at', 'No date')}")
                print(f"   Engagement: {post.get('likes', 0)} likes, {post.get('comments', 0)} comments")
                print(f"   URL: {post.get('url', 'No URL')}")
            if len(posts) > 5:
                print(f"\n   ... and {len(posts) - 5} more posts")
            print("")

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

    async def _trigger_and_fetch_posts(self, profile_url: str, timeout_seconds: int = 120) -> Optional[List[Dict[str, Any]]]:
        """
        Trigger LinkedIn posts scraping job and return posts.
        Handles both synchronous (HTTP 200 with JSONL) and asynchronous (HTTP 202 with snapshot_id) responses.
        """
        print(f"🚀 Fetching posts for: {profile_url}")
        logger.info(f"🚀 Fetching posts for: {profile_url}")
        try:
            url = f"{self.base_url}/datasets/v3/scrape"
            params = {
                "dataset_id": self.dataset_id,
                "notify": "false",
                "include_errors": "true",
                "type": "discover_new",
                "discover_by": "profile_url"
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            body = {
                "input": [{"url": profile_url}]  # NO start_date/end_date - they filter out posts without dates
            }

            logger.info(f"🔧 Calling Bright Data API: {url}")

            # Use extended timeout since scraping can take time
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, params=params, headers=headers, json=body)

            logger.info(f"🔧 Response status: {response.status_code}")
            print(f"🔧 Response status: {response.status_code}")

            # Handle HTTP 202 - Async mode with snapshot_id
            if response.status_code == 202:
                try:
                    data = response.json()
                    snapshot_id = data.get("snapshot_id")
                    if snapshot_id:
                        logger.info(f"📸 Got snapshot_id: {snapshot_id}, polling for results...")
                        print(f"📸 Got snapshot_id: {snapshot_id}, polling for results...")
                        return await self._poll_and_download(snapshot_id, timeout_seconds)
                    else:
                        logger.error(f"HTTP 202 but no snapshot_id in response: {data}")
                        return None
                except json.JSONDecodeError:
                    logger.error(f"HTTP 202 but response is not JSON: {response.text}")
                    return None

            # Handle HTTP 200 - Synchronous mode with JSONL
            elif response.status_code == 200:
                # Parse JSONL response (one JSON object per line)
                response_text = response.text.strip()
                if not response_text:
                    logger.warning("Empty response from Bright Data")
                    return []

                posts = []
                for line in response_text.split('\n'):
                    line = line.strip()
                    if line:
                        try:
                            post = json.loads(line)
                            posts.append(post)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSONL line: {e}")
                            continue

                logger.info(f"✅ Fetched {len(posts)} posts from Bright Data (synchronous)")
                print(f"✅ Fetched {len(posts)} posts from Bright Data (synchronous)")
                return posts

            # Handle errors
            else:
                logger.error(f"Scraping failed: HTTP {response.status_code}: {response.text}")
                print(f"❌ Scraping failed: HTTP {response.status_code}")
                return None

        except Exception as e:
            import traceback
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else repr(e)
            full_traceback = traceback.format_exc()

            logger.error(f"Error fetching posts [{error_type}]: {error_msg}")
            logger.error(f"Full traceback:\n{full_traceback}")
            print(f"❌ Exception fetching posts [{error_type}]: {error_msg}")
            return None

    async def _poll_and_download(self, snapshot_id: str, timeout_seconds: int) -> Optional[List[Dict[str, Any]]]:
        """Poll snapshot status and download results when ready"""
        try:
            poll_url = f"{self.base_url}/datasets/v3/progress/{snapshot_id}"
            download_url = f"{self.base_url}/datasets/v3/snapshot/{snapshot_id}"
            headers = {"Authorization": f"Bearer {self.api_token}"}

            start_time = datetime.now()
            poll_interval = 5  # Start with 5 seconds
            max_wait = timeout_seconds

            async with httpx.AsyncClient(timeout=30) as client:
                while (datetime.now() - start_time).total_seconds() < max_wait:
                    # Check progress
                    progress_response = await client.get(poll_url, headers=headers)

                    if progress_response.status_code != 200:
                        logger.error(f"Progress check failed: HTTP {progress_response.status_code}")
                        await asyncio.sleep(poll_interval)
                        continue

                    progress_data = progress_response.json()
                    status = progress_data.get("status")

                    logger.info(f"📊 Snapshot status: {status}")

                    if status == "ready":
                        # Download results
                        download_response = await client.get(download_url, headers=headers)

                        if download_response.status_code != 200:
                            logger.error(f"Download failed: HTTP {download_response.status_code}")
                            return None

                        # Bright Data returns JSONL (JSON Lines) - one JSON object per line
                        response_text = download_response.text.strip()
                        if not response_text:
                            logger.warning("Empty response from Bright Data")
                            return []

                        posts = []
                        for line in response_text.split('\n'):
                            line = line.strip()
                            if line:
                                try:
                                    post = json.loads(line)
                                    posts.append(post)
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse JSONL line: {e}")
                                    continue

                        logger.info(f"📥 Downloaded {len(posts)} posts from snapshot")
                        return posts

                    elif status in ["failed", "error"]:
                        error_msg = progress_data.get("error", "Unknown error")
                        logger.error(f"Scraping job failed: {error_msg}")
                        return None

                    # Still building - wait and retry
                    await asyncio.sleep(poll_interval)
                    poll_interval = min(poll_interval + 2, 15)  # Increase interval up to 15s

                logger.error(f"Timeout waiting for snapshot {snapshot_id} after {max_wait}s")
                return None

        except Exception as e:
            logger.error(f"Error polling/downloading: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

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
        # Extract text content - Bright Data uses post_text or original_post_text
        text = (
            raw_post.get("post_text") or
            raw_post.get("original_post_text") or
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

        # Extract creation date/time - Bright Data uses date_posted
        created_at = (
            raw_post.get("date_posted") or
            raw_post.get("created_at") or
            raw_post.get("createdAt") or
            raw_post.get("postedDate") or
            raw_post.get("publishedAt") or
            raw_post.get("date") or
            raw_post.get("timestamp") or
            datetime.now(timezone.utc).isoformat()
        )

        # Normalize date to ISO format
        created_at = self._normalize_date(created_at)

        # Extract author information - Bright Data uses user_id
        author = (
            raw_post.get("author") or
            raw_post.get("authorName") or
            raw_post.get("user_id") or
            raw_post.get("creator") or
            raw_post.get("name") or
            "Unknown"
        )

        # Build author URL from user_id if available
        author_url = raw_post.get("author_url") or raw_post.get("authorUrl") or raw_post.get("authorProfileUrl") or raw_post.get("profileUrl")

        if not author_url and raw_post.get("user_id"):
            # Construct LinkedIn profile URL from user_id
            author_url = f"https://www.linkedin.com/in/{raw_post['user_id']}"
        elif not author_url:
            author_url = profile_url  # Fallback to input profile URL

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
