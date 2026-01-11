"""
Apify Google Search Service - X-Ray Method Implementation

Uses Google search with dork queries (site: operators) to find high-quality signals
instead of direct social media scraping.

Strategy: "Use Google as Your Filter"
- Google has already filtered bots, spam, low-quality posts
- Dork queries extract only high-intent signals
- Much cheaper and cleaner than broad scrapers

Actor: apidojo/google-search-scraper (cheapest option at $0.002/query)
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from apify_client import ApifyClient
from app.core.config import settings
from app.domain.schemas.signal_refinery_schema import (
    XRayPlatformEnum,
    XRaySearchResult,
    DorkQueryPreview
)
import logging

logger = logging.getLogger(__name__)


class ApifyGoogleSearchService:
    """Service for Google X-Ray search using Apify"""

    # Primary actor (cheapest)
    PRIMARY_ACTOR_ID = "apidojo/google-search-scraper"

    # Fallback actor (official, more reliable)
    FALLBACK_ACTOR_ID = "apify/google-search-scraper"

    def __init__(self):
        """Initialize Apify client"""
        if not settings.APIFY_API_TOKEN:
            logger.warning("APIFY_API_TOKEN not configured")
            self.apify_client = None
        else:
            self.apify_client = ApifyClient(settings.APIFY_API_TOKEN)

    @staticmethod
    def build_dork_query(
        platform: XRayPlatformEnum,
        keyword: str,
        location: str = "Nigeria",
        custom_filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build Google dork query for X-Ray search

        Dork Query = Advanced Google search operators to find high-intent signals

        Pattern: site:{platform} {intent_signals} "{keyword}" "{location}" {filters}
        """

        # Intent signals (buying keywords)
        intent_signals = '(intext:"looking for" OR intext:"need" OR intext:"recommend" OR intext:"wanted" OR intext:"help find")'

        # Problem signals (pain points)
        problem_signals = '(intext:"problem" OR intext:"issue" OR intext:"expensive" OR intext:"struggling")'

        # Build query based on platform
        if platform == XRayPlatformEnum.TWITTER:
            # Twitter X-Ray: Focus on main posts, exclude replies
            site = "site:twitter.com"
            filters = '-inurl:status -inurl:reply'  # Exclude reply threads

            query = f'{site} {intent_signals} "{keyword}" "{location}" {filters}'

        elif platform == XRayPlatformEnum.NAIRALAND:
            # Nairaland: Nigerian forum, rich context
            site = "site:nairaland.com"

            # Get posts from last 60 days (Nairaland specific)
            cutoff_date = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d")
            time_filter = f'after:{cutoff_date}'

            query = f'{site} "{keyword}" {problem_signals} {time_filter}'

        elif platform == XRayPlatformEnum.LINKEDIN:
            # LinkedIn: Posts and articles (not job postings - we have separate scraper for that)
            site = "site:linkedin.com/posts OR site:linkedin.com/pulse"
            filters = '-inurl:jobs'  # Exclude job listings

            query = f'{site} {intent_signals} "{keyword}" "{location}" {filters}'

        elif platform == XRayPlatformEnum.REDDIT:
            # Reddit: Subreddit discussions
            site = "site:reddit.com"

            query = f'{site} {intent_signals} "{keyword}" "{location}"'

        else:
            # Generic fallback
            query = f'{intent_signals} "{keyword}" "{location}"'

        # Apply custom filters if provided
        if custom_filters:
            if custom_filters.get("exclude_keywords"):
                excludes = " ".join([f'-"{word}"' for word in custom_filters["exclude_keywords"]])
                query += f' {excludes}'

            if custom_filters.get("required_keywords"):
                includes = " ".join([f'"{word}"' for word in custom_filters["required_keywords"]])
                query += f' {includes}'

        logger.info(f"📍 Built dork query for {platform.value}: {query}")
        return query

    @staticmethod
    def preview_dork_queries(
        keyword: str,
        platforms: List[XRayPlatformEnum],
        location: str = "Nigeria"
    ) -> List[DorkQueryPreview]:
        """
        Preview dork queries that will be used (useful for frontend display)
        """
        previews = []
        for platform in platforms:
            query = ApifyGoogleSearchService.build_dork_query(platform, keyword, location)
            previews.append(DorkQueryPreview(
                platform=platform,
                query=query,
                estimated_results=None  # We don't know until we run it
            ))
        return previews

    async def search(
        self,
        dork_query: str,
        max_results: int = 50,
        country_code: str = "ng",  # Nigeria
        use_fallback_actor: bool = False
    ) -> List[XRaySearchResult]:
        """
        Execute Google search with dork query

        Args:
            dork_query: The Google dork query (from build_dork_query)
            max_results: Maximum results to fetch
            country_code: Country code (ng = Nigeria)
            use_fallback_actor: Use official Apify actor instead of cheaper one

        Returns:
            List of search results
        """
        if not self.apify_client:
            logger.error("Apify client not initialized")
            return []

        try:
            # Choose actor
            actor_id = self.FALLBACK_ACTOR_ID if use_fallback_actor else self.PRIMARY_ACTOR_ID
            logger.info(f"🔍 Running Google X-Ray search with actor: {actor_id}")
            logger.info(f"   Query: {dork_query}")
            logger.info(f"   Max results: {max_results}")

            # Configure input based on actor
            if actor_id == self.PRIMARY_ACTOR_ID:
                # apidojo/google-search-scraper
                run_input = {
                    "queries": [dork_query],
                    "maxResults": max_results,
                    "countryCode": country_code,
                    "languageCode": "en",
                    "includeUnfilteredResults": False
                }
            else:
                # apify/google-search-scraper (official)
                run_input = {
                    "queries": [dork_query],
                    "maxPagesPerQuery": max(1, max_results // 10),  # 10 results per page
                    "resultsPerPage": 10,
                    "countryCode": country_code,
                    "languageCode": "en"
                }

            # Run the actor
            logger.info(f"   Starting Apify actor run...")
            run = self.apify_client.actor(actor_id).call(run_input=run_input)

            # Check status
            if run.get("status") != "SUCCEEDED":
                error_msg = f"Apify actor run failed with status: {run.get('status', 'Unknown')}"
                logger.error(error_msg)
                return []

            # Get results
            items = []
            try:
                for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                    items.append(item)
                logger.info(f"   ✅ Fetched {len(items)} results from Google")
            except Exception as dataset_error:
                logger.error(f"   ❌ Error reading dataset: {str(dataset_error)}")
                return []

            # Parse results
            results = self._parse_google_results(items, dork_query)
            logger.info(f"   ✅ Parsed {len(results)} valid results")

            return results

        except Exception as e:
            logger.error(f"❌ Error in Google X-Ray search: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_google_results(
        self,
        items: List[Dict[str, Any]],
        dork_query: str
    ) -> List[XRaySearchResult]:
        """
        Parse raw Apify results into XRaySearchResult objects
        """
        results = []

        for idx, item in enumerate(items):
            try:
                # Extract fields (structure varies by actor)
                title = item.get("title", item.get("name", ""))
                snippet = item.get("description", item.get("snippet", ""))
                url = item.get("url", item.get("link", ""))

                if not url:
                    logger.warning(f"   Skipping result {idx+1}: No URL found")
                    continue

                # Try to extract date
                source_date = None
                date_str = item.get("date", item.get("publishedDate"))
                if date_str:
                    try:
                        source_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except:
                        pass

                # Determine platform from URL
                platform = self._detect_platform_from_url(url)

                result = XRaySearchResult(
                    platform=platform,
                    title=title,
                    snippet=snippet,
                    url=url,
                    source_date=source_date,
                    google_rank=idx + 1,  # Position in results
                    dork_query=dork_query,
                    raw_data=item  # Store full raw data for debugging
                )

                results.append(result)

            except Exception as e:
                logger.warning(f"   Error parsing result {idx+1}: {str(e)}")
                continue

        return results

    @staticmethod
    def _detect_platform_from_url(url: str) -> XRayPlatformEnum:
        """Detect platform from URL"""
        url_lower = url.lower()

        if "twitter.com" in url_lower or "x.com" in url_lower:
            return XRayPlatformEnum.TWITTER
        elif "nairaland.com" in url_lower:
            return XRayPlatformEnum.NAIRALAND
        elif "linkedin.com" in url_lower:
            return XRayPlatformEnum.LINKEDIN
        elif "reddit.com" in url_lower:
            return XRayPlatformEnum.REDDIT
        else:
            # Default to Twitter if uncertain
            return XRayPlatformEnum.TWITTER

    async def search_multiple_platforms(
        self,
        keyword: str,
        platforms: List[XRayPlatformEnum],
        location: str = "Nigeria",
        max_results_per_platform: int = 50
    ) -> Dict[XRayPlatformEnum, List[XRaySearchResult]]:
        """
        Search across multiple platforms in parallel

        Returns:
            Dict mapping platform to results
        """
        logger.info(f"🔍 Starting multi-platform X-Ray search")
        logger.info(f"   Keyword: {keyword}")
        logger.info(f"   Platforms: {[p.value for p in platforms]}")
        logger.info(f"   Location: {location}")

        # Build dork queries for each platform
        tasks = []
        platform_queries = {}

        for platform in platforms:
            dork_query = self.build_dork_query(platform, keyword, location)
            platform_queries[platform] = dork_query

            # Create async task for each platform
            task = self.search(dork_query, max_results_per_platform)
            tasks.append((platform, task))

        # Run all searches in parallel
        results_by_platform = {}

        for platform, task in tasks:
            try:
                results = await task
                results_by_platform[platform] = results
                logger.info(f"   ✅ {platform.value}: {len(results)} results")
            except Exception as e:
                logger.error(f"   ❌ {platform.value}: Error - {str(e)}")
                results_by_platform[platform] = []

        total_results = sum(len(r) for r in results_by_platform.values())
        logger.info(f"✅ Multi-platform search complete: {total_results} total results")

        return results_by_platform
