"""
ApifyJobbermanService - Scrapes Jobberman using Apify or custom scraper
Pattern: Same as ApifyLinkedInJobsService but for Jobberman

This service fetches job postings from Jobberman (Nigerian job board) using Apify actors.
"""
import asyncio
from typing import List, Dict, Any, Optional
from apify_client import ApifyClient
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class ApifyJobbermanService:
    """
    Service to fetch job postings from Jobberman using Apify
    Pattern: Same as ApifyLinkedInJobsService
    """

    def __init__(self):
        """
        Initialize the service with Apify client
        """
        if not settings.APIFY_API_TOKEN:
            logger.warning("APIFY_API_TOKEN not configured. Jobberman scraping will not work.")
            self.apify_client = None
        else:
            self.apify_client = ApifyClient(settings.APIFY_API_TOKEN)

    async def fetch_job_postings(
        self,
        search_query: str,
        max_jobs: int = 5,
        location: str = "Nigeria"
    ) -> Dict[str, Any]:
        """
        Fetch job postings from Jobberman using Apify

        Args:
            search_query: The search query (e.g., "DevOps Engineer")
            max_jobs: Maximum number of jobs to fetch (default: 5)
            location: Geographic location filter (default: "Nigeria")

        Returns:
            Dictionary containing jobs and metadata:
            {
                "success": True,
                "total_jobs": 5,
                "jobs": [{
                    "title": "Backend Developer",
                    "company": "Nigerian Fintech Ltd",
                    "location": "Lagos, Nigeria",
                    "description": "We are seeking...",
                    "url": "https://jobberman.com/job/...",
                    "posted_date": "2025-12-15T10:00:00Z",
                    "salary": "NGN 200,000 - 350,000"  # if available
                }],
                "search_query": "DevOps Engineer"
            }
        """
        try:
            # Check if client is initialized
            if not self.apify_client:
                return {
                    "success": False,
                    "error_message": "Apify client not initialized. Please configure APIFY_API_TOKEN.",
                    "jobs": []
                }

            # Fetch jobs from Apify
            jobs_result = await self._fetch_jobs_from_apify(search_query, max_jobs, location)

            if not jobs_result["success"]:
                return jobs_result

            jobs = jobs_result["jobs"]

            return {
                "success": True,
                "total_jobs": len(jobs),
                "jobs": jobs,
                "search_query": search_query
            }

        except Exception as e:
            logger.error(f"Error in fetch_job_postings (Jobberman): {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": f"An error occurred: {str(e)}",
                "jobs": []
            }

    async def _fetch_jobs_from_apify(
        self,
        search_query: str,
        max_jobs: int,
        location: str
    ) -> Dict[str, Any]:
        """
        Fetch job postings from Apify using Jobberman scraper actor

        Args:
            search_query: Job search query
            max_jobs: Maximum number of jobs to fetch
            location: Geographic location

        Returns:
            Dictionary containing the fetched jobs
        """
        try:
            # Jobberman Scraper actor from Apify Store
            # Actor: shahidirfan/jobberman-job-scraper
            # Docs: https://apify.com/shahidirfan/jobberman-job-scraper
            actor_id = "shahidirfan/jobberman-job-scraper"

            # Configure the input for the Jobberman actor
            # Note: Jobberman uses 'keyword' not 'search'
            run_input = {
                "keyword": search_query,  # Jobberman uses 'keyword' instead of 'search'
                "location": location,
                "posted_date": "anytime",  # Options: anytime, last_24_hours, last_7_days, last_14_days, last_30_days
                "proxyConfiguration": {"useApifyProxy": True},  # Use Apify proxies to prevent blocking
            }

            # Run the actor in a thread to avoid blocking
            logger.info(f"Starting Apify actor to fetch Jobberman jobs for: {search_query} in {location}")

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
                    "jobs": []
                }

            # Get the results
            items = []
            try:
                dataset_id = run["defaultDatasetId"]
                for item in self.apify_client.dataset(dataset_id).iterate_items():
                    items.append(item)

                # Log the first item structure for debugging
                if items:
                    logger.debug(f"Sample Jobberman job item structure: {list(items[0].keys())}")

            except Exception as dataset_error:
                logger.error(f"Error reading dataset: {str(dataset_error)}")
                return {
                    "success": False,
                    "error_message": f"Failed to read results from Apify: {str(dataset_error)}",
                    "jobs": []
                }

            # Process the results
            jobs = []
            for item in items[:max_jobs]:
                try:
                    # Extract job information from Jobberman actor output
                    # The shahidirfan/jobberman-job-scraper returns fields like:
                    # title, company, location, description, url, salary, etc.
                    job_data = {
                        "title": item.get("title") or item.get("jobTitle") or item.get("job_title") or "Unknown Title",
                        "company": item.get("company") or item.get("companyName") or item.get("company_name") or "Unknown Company",
                        "location": item.get("location") or item.get("jobLocation") or item.get("job_location") or location,
                        "description": item.get("description") or item.get("jobDescription") or item.get("job_description") or "",
                        "url": item.get("url") or item.get("link") or item.get("jobUrl") or item.get("job_url") or "",
                        "posted_date": self._parse_posted_date(item.get("postedDate") or item.get("posted_date") or item.get("publishedAt")),
                        "salary": item.get("salary") or item.get("salaryRange") or item.get("salary_range"),
                        "source": "Jobberman"
                    }

                    # Only add jobs with valid URLs and descriptions
                    if job_data["url"] and job_data["description"]:
                        jobs.append(job_data)
                    else:
                        logger.warning(f"Skipping Jobberman job with missing URL or description: {job_data['title']}")

                except Exception as item_error:
                    logger.warning(f"Error processing Jobberman job item: {str(item_error)}")
                    continue

            logger.info(f"Successfully fetched {len(jobs)} Jobberman jobs")

            return {
                "success": True,
                "jobs": jobs
            }

        except Exception as e:
            logger.error(f"Error fetching jobs from Apify (Jobberman): {str(e)}")
            import traceback
            traceback.print_exc()

            # Fallback: Return empty results for now if actor doesn't exist
            logger.warning("Jobberman scraper not configured. Returning empty results.")
            return {
                "success": True,  # Don't fail the entire job fetch
                "jobs": []  # Just return no Jobberman jobs
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
            logger.warning(f"Could not parse date '{date_str}': {str(e)}")
            return datetime.now(timezone.utc).isoformat()
