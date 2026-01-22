"""
ApifyLinkedInPostScraperService - Scrapes LinkedIn Posts using Apify

This service fetches LinkedIn posts/activity from user profiles or company pages
using the supreme_coder/linkedin-post Apify actor.

Used by Lazarus Protocol to monitor Focus Contacts with LinkedIn URLs for buying signals.
"""
import asyncio
from typing import List, Dict, Any, Optional
from apify_client import ApifyClient
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class ApifyLinkedInPostScraperService:
    """
    Service to fetch LinkedIn posts/activity using Apify
    Actor: supreme_coder/linkedin-post
    """

    def __init__(self):
        """
        Initialize the service with Apify client
        """
        if not settings.APIFY_API_TOKEN:
            logger.warning("APIFY_API_TOKEN not configured. LinkedIn post scraping will not work.")
            self.apify_client = None
        else:
            self.apify_client = ApifyClient(settings.APIFY_API_TOKEN)

    async def fetch_linkedin_posts(
        self,
        linkedin_urls: List[str],
        deep_scrape: bool = True,
        limit_per_source: int = 10,
        raw_data: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch LinkedIn posts from user profiles or company pages using Apify

        Args:
            linkedin_urls: List of LinkedIn URLs to scrape (profiles, companies, or search URLs)
            deep_scrape: Enable deep scraping for more detailed data (default: True)
            limit_per_source: Maximum number of posts to fetch per URL (default: 10)
            raw_data: Return raw data from LinkedIn (default: False)

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
                            "shares": 3
                        }
                    ]
                },
                "all_posts": [...]  # Flattened list of all posts
            }
        """
        try:
            # Validate inputs
            if not linkedin_urls:
                return {
                    "success": False,
                    "error_message": "No LinkedIn URLs provided",
                    "posts_by_url": {},
                    "all_posts": []
                }

            # Check if client is initialized
            if not self.apify_client:
                return {
                    "success": False,
                    "error_message": "Apify client not initialized. Please configure APIFY_API_TOKEN.",
                    "posts_by_url": {},
                    "all_posts": []
                }

            # Filter and validate LinkedIn URLs
            valid_urls = []
            for url in linkedin_urls:
                if url and "linkedin.com" in url:
                    valid_urls.append(url)
                else:
                    logger.warning(f"Skipping invalid LinkedIn URL: {url}")

            if not valid_urls:
                return {
                    "success": False,
                    "error_message": "No valid LinkedIn URLs found",
                    "posts_by_url": {},
                    "all_posts": []
                }

            # Fetch posts from Apify
            posts_result = await self._fetch_posts_from_apify(
                valid_urls,
                deep_scrape,
                limit_per_source,
                raw_data
            )

            if not posts_result["success"]:
                return posts_result

            posts_by_url = posts_result["posts_by_url"]
            all_posts = posts_result["all_posts"]

            logger.info(f"✅ Successfully fetched {len(all_posts)} LinkedIn posts from {len(valid_urls)} URLs")

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

    async def _fetch_posts_from_apify(
        self,
        urls: List[str],
        deep_scrape: bool,
        limit_per_source: int,
        raw_data: bool
    ) -> Dict[str, Any]:
        """
        Fetch LinkedIn posts from Apify using supreme_coder/linkedin-post actor

        Args:
            urls: List of LinkedIn URLs
            deep_scrape: Enable deep scraping
            limit_per_source: Max posts per URL
            raw_data: Return raw data

        Returns:
            Dictionary containing the fetched posts grouped by URL
        """
        try:
            # LinkedIn Post Scraper actor from Apify Store
            # Actor: supreme_coder/linkedin-post
            # Docs: https://apify.com/supreme_coder/linkedin-post
            actor_id = "supreme_coder/linkedin-post"

            # Configure the input for the actor
            run_input = {
                "deepScrape": deep_scrape,
                "limitPerSource": limit_per_source,
                "rawData": raw_data,
                "urls": urls
            }

            logger.info(f"🚀 Starting Apify actor to fetch LinkedIn posts from {len(urls)} URLs")
            logger.info(f"   Deep scrape: {deep_scrape}, Limit per source: {limit_per_source}")

            # Run actor synchronously in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            run = await loop.run_in_executor(
                None,
                lambda: self.apify_client.actor(actor_id).call(run_input=run_input)
            )

            # Check if the run was successful
            if run.get("status") != "SUCCEEDED":
                error_msg = f"Apify actor run failed with status: {run.get('status', 'Unknown')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error_message": error_msg,
                    "posts_by_url": {},
                    "all_posts": []
                }

            # Get the results from dataset
            items = []
            try:
                dataset_id = run["defaultDatasetId"]
                for item in self.apify_client.dataset(dataset_id).iterate_items():
                    items.append(item)

                logger.info(f"📦 Retrieved {len(items)} items from Apify dataset")

                # Log the first item structure for debugging
                if items:
                    logger.debug(f"Sample LinkedIn post item structure: {list(items[0].keys())}")

            except Exception as dataset_error:
                logger.error(f"Error reading dataset: {str(dataset_error)}")
                return {
                    "success": False,
                    "error_message": f"Failed to read results from Apify: {str(dataset_error)}",
                    "posts_by_url": {},
                    "all_posts": []
                }

            # Process the results and group by URL
            posts_by_url: Dict[str, List[Dict[str, Any]]] = {url: [] for url in urls}
            all_posts = []

            for item in items:
                try:
                    # Extract post information
                    # Field names may vary - handle common variations
                    post_data = {
                        "text": item.get("text") or item.get("content") or item.get("postText") or "",
                        "url": item.get("url") or item.get("postUrl") or item.get("link") or "",
                        "created_at": self._parse_posted_date(item.get("postedDate") or item.get("createdAt") or item.get("publishedAt")),
                        "author": item.get("author") or item.get("authorName") or item.get("creator") or "Unknown",
                        "author_url": item.get("authorUrl") or item.get("authorProfileUrl") or item.get("profileUrl") or "",
                        "likes": item.get("likes") or item.get("numLikes") or item.get("likeCount") or 0,
                        "comments": item.get("comments") or item.get("numComments") or item.get("commentCount") or 0,
                        "shares": item.get("shares") or item.get("numShares") or item.get("shareCount") or 0,
                        "source": "LinkedIn",
                        "raw_data": item if raw_data else None
                    }

                    # Only add posts with valid text content
                    if post_data["text"]:
                        # Try to match this post to its source URL
                        source_url = item.get("sourceUrl") or item.get("inputUrl")
                        if source_url and source_url in posts_by_url:
                            posts_by_url[source_url].append(post_data)
                        else:
                            # If we can't match to source, add to all URLs (fallback)
                            # This happens when actor doesn't return sourceUrl
                            for url in urls:
                                if item.get("authorUrl") and url in item.get("authorUrl", ""):
                                    posts_by_url[url].append(post_data)
                                    break
                            else:
                                # Add to first URL as last resort
                                if urls:
                                    posts_by_url[urls[0]].append(post_data)

                        all_posts.append(post_data)
                    else:
                        logger.warning(f"Skipping post with missing text content")

                except Exception as item_error:
                    logger.warning(f"Error processing LinkedIn post item: {str(item_error)}")
                    continue

            logger.info(f"✅ Successfully processed {len(all_posts)} LinkedIn posts")

            return {
                "success": True,
                "posts_by_url": posts_by_url,
                "all_posts": all_posts
            }

        except Exception as e:
            logger.error(f"Error fetching posts from Apify: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": str(e),
                "posts_by_url": {},
                "all_posts": []
            }

    def _parse_posted_date(self, date_str: Optional[str]) -> str:
        """
        Parse posted date from various formats to ISO format

        Args:
            date_str: Date string from LinkedIn post

        Returns:
            ISO formatted date string or current date if parsing fails
        """
        if not date_str:
            return datetime.now(timezone.utc).isoformat()

        try:
            # Try ISO format first
            if "T" in str(date_str):
                return str(date_str)

            # Try common date formats
            from dateutil import parser
            parsed_date = parser.parse(str(date_str))
            return parsed_date.isoformat()

        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {str(e)}")
            return datetime.now(timezone.utc).isoformat()
