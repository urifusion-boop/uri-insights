"""
ApifyIndeedService - Scrapes Indeed Jobs using Apify
Pattern: Same as ApifyLinkedInJobsService and ApifyJobbermanService

This service fetches job postings from Indeed using Apify actors.
Currently configured for easy integration when Indeed actor is ready.
"""
import asyncio
from typing import List, Dict, Any, Optional
from apify_client import ApifyClient
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class ApifyIndeedService:
    """
    Service to fetch job postings from Indeed using Apify
    Pattern: Same as ApifyLinkedInJobsService

    Status: Ready for integration - just needs Indeed actor ID
    """

    def __init__(self):
        """
        Initialize the service with Apify client
        """
        if not settings.APIFY_API_TOKEN:
            logger.warning("APIFY_API_TOKEN not configured. Indeed scraping will not work.")
            self.apify_client = None
        else:
            self.apify_client = ApifyClient(settings.APIFY_API_TOKEN)

    async def fetch_job_postings(
        self,
        search_query: str,
        max_jobs: int = 10,
        location: str = "Nigeria",
        country: str = "NG"
    ) -> Dict[str, Any]:
        """
        Fetch job postings from Indeed using Apify (misceres/indeed-scraper)

        Args:
            search_query: The search query (e.g., "DevOps Engineer")
            max_jobs: Maximum number of jobs to fetch (default: 10)
            location: Geographic location filter (default: "Nigeria")
            country: Country code for Indeed (default: "NG" for Nigeria)

        Returns:
            Dictionary containing jobs and metadata:
            {
                "success": True,
                "total_jobs": 10,
                "jobs": [{
                    "title": "Senior Backend Engineer",
                    "company": "TechCorp Ltd",
                    "location": "Lagos, Nigeria",
                    "description": "We are looking for...",
                    "url": "https://indeed.com/viewjob?jk=123",
                    "posted_date": "2025-12-15T10:00:00Z",
                    "salary": "$80,000 - $120,000"  # if available
                }],
                "search_query": "DevOps Engineer"
            }
        """
        try:
            # Check if client is initialized
            if not self.apify_client:
                logger.warning("Indeed scraper: Apify client not initialized")
                return {
                    "success": False,
                    "error_message": "Apify client not initialized. Please configure APIFY_API_TOKEN.",
                    "jobs": []
                }

            # Fetch jobs from Apify using misceres/indeed-scraper
            jobs_result = await self._fetch_jobs_from_apify(search_query, max_jobs, location, country)

            if not jobs_result["success"]:
                return jobs_result

            jobs = jobs_result["jobs"]

            return {
                "success": True,
                "total_jobs": len(jobs),
                "jobs": jobs,
                "search_query": search_query,
                "location": location
            }

        except Exception as e:
            logger.error(f"Error fetching Indeed jobs: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error_message": f"Error fetching Indeed jobs: {str(e)}",
                "jobs": []
            }

    async def _fetch_jobs_from_apify(
        self,
        search_query: str,
        max_jobs: int,
        location: str,
        country: str = "NG"
    ) -> Dict[str, Any]:
        """
        Fetch jobs from Indeed via Apify using misceres/indeed-scraper

        Args:
            search_query: Search query (e.g., "DevOps Engineer")
            max_jobs: Max jobs to fetch
            location: Location filter (e.g., "Lagos", "Nigeria")
            country: Country code (e.g., "NG", "US", "UK")

        Returns:
            Dict with jobs data
        """
        try:
            # Using misceres/indeed-scraper - reliable and well-maintained
            # Docs: https://apify.com/misceres/indeed-scraper
            actor_id = "misceres/indeed-scraper"

            # Map common location strings to country codes
            country_code_map = {
                "nigeria": "NG",
                "united states": "US",
                "uk": "UK",
                "united kingdom": "UK",
                "canada": "CA",
                "south africa": "ZA",
                "kenya": "KE",
                "ghana": "GH",
            }

            # Auto-detect country code from location if not provided
            if not country or country == "NG":
                location_lower = location.lower()
                for country_name, code in country_code_map.items():
                    if country_name in location_lower:
                        country = code
                        break

            # Prepare actor input (matching misceres/indeed-scraper format)
            run_input = {
                "position": search_query,
                "location": location,
                "country": country,
                "maxItemsPerSearch": max_jobs,
                "parseCompanyDetails": False,  # Skip for speed
                "saveOnlyUniqueItems": True,
                "followApplyRedirects": False
            }

            logger.info(f"🔍 Fetching Indeed jobs: '{search_query}' in {location} ({country})")
            logger.info(f"   Using actor: {actor_id}")

            # Run the actor in executor to avoid blocking
            loop = asyncio.get_event_loop()
            run = await loop.run_in_executor(
                None,
                lambda: self.apify_client.actor(actor_id).call(run_input=run_input)
            )

            # Check if run succeeded
            if run.get("status") != "SUCCEEDED":
                error_msg = f"Indeed actor failed with status: {run.get('status', 'Unknown')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error_message": error_msg,
                    "jobs": []
                }

            # Fetch results from dataset
            items = []
            try:
                dataset_id = run["defaultDatasetId"]
                for item in self.apify_client.dataset(dataset_id).iterate_items():
                    items.append(item)

                logger.info(f"   📊 Indeed returned {len(items)} job postings")

            except Exception as dataset_error:
                logger.error(f"Error reading Indeed dataset: {str(dataset_error)}")
                return {
                    "success": False,
                    "error_message": f"Failed to read results: {str(dataset_error)}",
                    "jobs": []
                }

            # Transform Indeed data to standardized format
            jobs = []
            for item in items[:max_jobs]:
                try:
                    # misceres/indeed-scraper returns these fields
                    job_data = {
                        "title": item.get("positionName") or item.get("title") or "Unknown Title",
                        "company": item.get("company") or item.get("companyName") or "Unknown Company",
                        "location": item.get("location") or location,
                        "description": item.get("description") or item.get("jobDescription") or "",
                        "url": item.get("url") or item.get("link") or "",
                        "posted_date": self._parse_posted_date(item.get("postedAt") or item.get("datePosted")),
                        "salary": item.get("salary") or item.get("salaryRange"),
                        "source": "Indeed"
                    }

                    # Only add jobs with valid URLs and descriptions
                    if job_data["url"] and job_data["description"]:
                        jobs.append(job_data)
                    else:
                        logger.warning(f"Skipping Indeed job with missing URL or description: {job_data['title']}")

                except Exception as item_error:
                    logger.warning(f"Error processing Indeed job item: {str(item_error)}")
                    continue

            logger.info(f"✅ Successfully processed {len(jobs)} Indeed jobs")

            return {
                "success": True,
                "jobs": jobs
            }

        except Exception as e:
            logger.error(f"Error fetching Indeed jobs via Apify: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error_message": f"Apify actor error: {str(e)}",
                "jobs": []
            }

    def _parse_posted_date(self, date_str: Optional[str]) -> str:
        """
        Parse posted date from various formats to ISO format

        Args:
            date_str: Date string from job posting

        Returns:
            ISO formatted date string or current date if parsing fails
        """
        if not date_str:
            return datetime.now(timezone.utc).isoformat()

        try:
            # Try ISO format first
            if "T" in date_str:
                return date_str

            # Try common date formats
            from dateutil import parser
            parsed_date = parser.parse(date_str)
            return parsed_date.isoformat()

        except Exception as e:
            logger.warning(f"Could not parse Indeed date '{date_str}': {str(e)}")
            return datetime.now(timezone.utc).isoformat()
