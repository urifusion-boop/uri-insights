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
        location: str = "Nigeria"
    ) -> Dict[str, Any]:
        """
        Fetch job postings from Indeed using Apify

        Args:
            search_query: The search query (e.g., "DevOps Engineer")
            max_jobs: Maximum number of jobs to fetch (default: 10)
            location: Geographic location filter (default: "Nigeria")

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

            # TODO: Replace with actual Indeed actor when available
            # For now, return placeholder to allow system to work
            logger.info(f"Indeed scraper called for query: '{search_query}' in {location}")
            logger.warning("Indeed actor not configured yet - returning empty results")

            return {
                "success": True,
                "total_jobs": 0,
                "jobs": [],
                "search_query": search_query,
                "location": location,
                "note": "Indeed integration ready - awaiting actor configuration"
            }

            # UNCOMMENT WHEN INDEED ACTOR IS READY:
            # jobs_result = await self._fetch_jobs_from_apify(search_query, max_jobs, location)
            #
            # if not jobs_result["success"]:
            #     return jobs_result
            #
            # jobs = jobs_result["jobs"]
            #
            # return {
            #     "success": True,
            #     "total_jobs": len(jobs),
            #     "jobs": jobs,
            #     "search_query": search_query,
            #     "location": location
            # }

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
        location: str
    ) -> Dict[str, Any]:
        """
        Internal method to fetch jobs from Indeed via Apify

        TODO: Configure with actual Indeed actor ID when available
        Recommended actors:
        - misceres/indeed-scraper
        - epctex/indeed-scraper
        - dtrungtin/indeed-scraper

        Args:
            search_query: Search query
            max_jobs: Max jobs to fetch
            location: Location filter

        Returns:
            Dict with jobs data
        """
        try:
            # TODO: Replace with actual Indeed actor ID
            # Example: INDEED_ACTOR_ID = "misceres/indeed-scraper"
            INDEED_ACTOR_ID = "REPLACE_WITH_ACTUAL_INDEED_ACTOR_ID"

            # Prepare actor input
            run_input = {
                "position": search_query,
                "location": location,
                "maxItems": max_jobs,
                "parseCompanyDetails": True,
                "saveOnlyUniqueItems": True,
                "followApplyRedirects": False
            }

            print(f"🔍 Calling Indeed Apify Actor: {INDEED_ACTOR_ID}")
            print(f"   Query: {search_query}")
            print(f"   Location: {location}")
            print(f"   Max jobs: {max_jobs}")

            # Run the actor
            run = self.apify_client.actor(INDEED_ACTOR_ID).call(run_input=run_input)

            # Fetch results from dataset
            items = []
            for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                items.append(item)

            print(f"✅ Indeed returned {len(items)} raw job postings")

            # Transform Indeed data to standardized format
            jobs = []
            for item in items[:max_jobs]:
                job = {
                    "title": item.get("positionName") or item.get("title", ""),
                    "company": item.get("company") or item.get("companyName", ""),
                    "location": item.get("location", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url") or item.get("link", ""),
                    "posted_date": item.get("postedAt") or item.get("datePosted"),
                    "salary": item.get("salary"),
                    "job_type": item.get("jobType"),
                    # Indeed-specific fields
                    "company_rating": item.get("companyRating"),
                    "company_reviews_count": item.get("companyReviewsCount"),
                }
                jobs.append(job)

            return {
                "success": True,
                "jobs": jobs
            }

        except Exception as e:
            logger.error(f"Apify Indeed fetch error: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error_message": f"Apify actor error: {str(e)}",
                "jobs": []
            }
