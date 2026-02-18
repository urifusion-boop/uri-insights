"""
BrightDataLinkedInJobsService - Scrapes LinkedIn Jobs using Bright Data
Replaces ApifyLinkedInJobsService with Bright Data API

This service fetches job postings from LinkedIn Jobs using Bright Data's dataset API.
Dataset ID: gd_lpfll7v5hcqtkxl6l
"""
import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BrightDataLinkedInJobsService:
    """
    Service to fetch job postings from LinkedIn Jobs using Bright Data

    Three fetching modes:
    1. Collect by URL - Fetch specific job URLs
    2. Discover by keyword - Search by keyword with filters (PRIMARY METHOD)
    3. Discover by URL - Scrape LinkedIn search result pages
    """

    BRIGHTDATA_API_URL = "https://api.brightdata.com/datasets/v3/scrape"
    BRIGHTDATA_DATASET_ID = "gd_lpfll7v5hcqtkxl6l"  # LinkedIn Jobs dataset
    BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY", "a3d28160-14ca-4c9a-842b-a505050241ff")

    def __init__(self):
        """Initialize the service"""
        if not self.BRIGHTDATA_API_KEY:
            logger.warning("BRIGHTDATA_API_KEY not configured. LinkedIn Jobs scraping will not work.")

    async def fetch_job_postings(
        self,
        search_query: str,
        max_jobs: int = 15,
        location: str = "Worldwide",
        published_at: str = "Past Month",
        solution_context: str = "",
        infer_parameters: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch job postings from LinkedIn Jobs using Bright Data keyword search

        This is the PRIMARY method - replaces ApifyLinkedInJobsService.fetch_job_postings()

        Args:
            search_query: The search query (e.g., "DevOps Engineer", "Python Developer")
            max_jobs: Maximum number of jobs to fetch (default: 15)
            location: Geographic location filter (e.g., "Lagos", "New York", "Worldwide")
            published_at: Time filter - "Past 24 hours", "Past Week", "Past Month", "Any Time"
            solution_context: Solution description for intelligent inference (not used with Bright Data)
            infer_parameters: Enable intelligent parameter inference (not used with Bright Data)

        Returns:
            Dictionary containing jobs and metadata:
            {
                "success": True,
                "total_jobs": 15,
                "jobs": [{
                    "title": "Senior Backend Engineer",
                    "company": "TechCorp Ltd",
                    "location": "Lagos, Nigeria",
                    "description": "We are looking for...",
                    "url": "https://linkedin.com/jobs/view/123",
                    "posted_date": "2025-12-15T10:00:00Z",
                    "salary": "$80,000 - $120,000"  # if available
                }],
                "search_query": "DevOps Engineer"
            }
        """
        try:
            # Map time filter to Bright Data format
            time_range_map = {
                "Past 24 hours": "Past 24 hours",
                "Past Week": "Past week",
                "Past Month": "Past month",
                "Any Time": ""
            }
            time_range = time_range_map.get(published_at, "Past month")

            # Use keyword discovery endpoint
            result = await self.fetch_jobs_by_keyword(
                keyword=search_query,
                location=location if location != "Worldwide" else "",
                time_range=time_range,
                max_results=max_jobs
            )

            if not result["success"]:
                return result

            return {
                "success": True,
                "total_jobs": len(result["jobs"]),
                "jobs": result["jobs"],
                "search_query": search_query
            }

        except Exception as e:
            logger.error(f"Error fetching LinkedIn jobs: {str(e)}")
            return {
                "success": False,
                "error_message": str(e),
                "jobs": []
            }

    async def fetch_jobs_by_keyword(
        self,
        keyword: str,
        location: str = "",
        country: str = "",
        time_range: str = "Past month",
        job_type: str = "",
        experience_level: str = "",
        remote: str = "",
        company: str = "",
        location_radius: str = "",
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        Fetch jobs using keyword search (Bright Data Discover by Keyword)

        Example:
            fetch_jobs_by_keyword(
                keyword="python developer",
                location="Lagos",
                country="NG",
                time_range="Past month",
                job_type="Full-time",
                experience_level="Mid-Senior level",
                remote="Remote"
            )

        Args:
            keyword: Job title/keyword (e.g., "python developer", "product manager")
            location: City/region (e.g., "Lagos", "New York", "Paris")
            country: 2-letter country code (e.g., "NG", "US", "FR")
            time_range: "Past 24 hours", "Past week", "Past month", "" (any time)
            job_type: "Full-time", "Part-time", "Contract", "Internship", "Temporary", "Volunteer"
            experience_level: "Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"
            remote: "On-site", "Remote", "Hybrid"
            company: Filter by company name
            location_radius: Distance radius (e.g., "10", "25", "50", "100")
            max_results: Maximum number of results to return

        Returns:
            {
                "success": True,
                "jobs": [...],
                "total_fetched": 20
            }
        """
        try:
            # Build request payload
            payload = {
                "input": [{
                    "keyword": keyword,
                    "location": location,
                    "country": country,
                    "time_range": time_range,
                    "job_type": job_type,
                    "experience_level": experience_level,
                    "remote": remote,
                    "company": company,
                    "location_radius": location_radius
                }]
            }

            # Make request to Bright Data
            url = f"{self.BRIGHTDATA_API_URL}?dataset_id={self.BRIGHTDATA_DATASET_ID}&notify=false&include_errors=true&type=discover_new&discover_by=keyword"

            headers = {
                "Authorization": f"Bearer {self.BRIGHTDATA_API_KEY}",
                "Content-Type": "application/json"
            }

            logger.info(f"🔍 Fetching LinkedIn jobs: keyword='{keyword}', location='{location}', time_range='{time_range}'")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                # Parse NDJSON response (newline-delimited JSON)
                raw_jobs = []
                for line in response.text.strip().split('\n'):
                    if line.strip():
                        job_json = httpx.Response(200, text=line).json()
                        raw_jobs.append(job_json)

                if not raw_jobs:
                    logger.warning(f"No jobs found for keyword: {keyword}")
                    return {"success": True, "jobs": [], "total_fetched": 0}


                # Transform to standard format
                jobs = []
                for job_data in raw_jobs[:max_results]:
                    transformed = self._transform_job_data(job_data)
                    if transformed:
                        jobs.append(transformed)

                logger.info(f"✅ Fetched {len(jobs)} LinkedIn jobs for '{keyword}'")

                return {
                    "success": True,
                    "jobs": jobs,
                    "total_fetched": len(raw_jobs)
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching jobs by keyword: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error_message": f"API error: {e.response.status_code}",
                "jobs": []
            }
        except Exception as e:
            logger.error(f"Error fetching jobs by keyword: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": str(e),
                "jobs": []
            }

    async def fetch_jobs_by_urls(
        self,
        job_urls: List[str]
    ) -> Dict[str, Any]:
        """
        Fetch specific job postings by their URLs (Bright Data Collect by URL)

        Example:
            fetch_jobs_by_urls([
                "https://www.linkedin.com/jobs/view/software-engineer-at-epic-3986111804",
                "https://www.linkedin.com/jobs/view/software-engineer-at-pave-4310512612/"
            ])

        Args:
            job_urls: List of LinkedIn job URLs

        Returns:
            {
                "success": True,
                "jobs": [...],
                "total_fetched": 2
            }
        """
        try:
            # Build request payload
            payload = {
                "input": [{"url": url} for url in job_urls]
            }

            url = f"{self.BRIGHTDATA_API_URL}?dataset_id={self.BRIGHTDATA_DATASET_ID}&notify=false&include_errors=true"

            headers = {
                "Authorization": f"Bearer {self.BRIGHTDATA_API_KEY}",
                "Content-Type": "application/json"
            }

            logger.info(f"🔍 Fetching {len(job_urls)} LinkedIn jobs by URL")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                # Parse NDJSON response
                raw_jobs = []
                for line in response.text.strip().split('\n'):
                    if line.strip():
                        raw_jobs.append(httpx.Response(200, text=line).json())

                # Transform to standard format
                jobs = []
                for job_data in raw_jobs:
                    transformed = self._transform_job_data(job_data)
                    if transformed:
                        jobs.append(transformed)

                logger.info(f"✅ Fetched {len(jobs)} LinkedIn jobs by URL")

                return {
                    "success": True,
                    "jobs": jobs,
                    "total_fetched": len(raw_jobs)
                }

        except Exception as e:
            logger.error(f"Error fetching jobs by URLs: {str(e)}")
            return {
                "success": False,
                "error_message": str(e),
                "jobs": []
            }

    async def fetch_jobs_by_search_url(
        self,
        search_urls: List[str]
    ) -> Dict[str, Any]:
        """
        Fetch jobs from LinkedIn search result URLs (Bright Data Discover by URL)

        Example:
            fetch_jobs_by_search_url([
                "https://www.linkedin.com/jobs/search?keywords=Software&location=Tel%20Aviv",
                "https://www.linkedin.com/jobs/reddit-inc.-jobs-worldwide?f_C=150573"
            ])

        Args:
            search_urls: List of LinkedIn search result URLs

        Returns:
            {
                "success": True,
                "jobs": [...],
                "total_fetched": 50
            }
        """
        try:
            # Build request payload
            payload = {
                "input": [{"url": url} for url in search_urls]
            }

            url = f"{self.BRIGHTDATA_API_URL}?dataset_id={self.BRIGHTDATA_DATASET_ID}&notify=false&include_errors=true&type=discover_new&discover_by=url"

            headers = {
                "Authorization": f"Bearer {self.BRIGHTDATA_API_KEY}",
                "Content-Type": "application/json"
            }

            logger.info(f"🔍 Fetching LinkedIn jobs from {len(search_urls)} search URLs")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                # Parse NDJSON response
                raw_jobs = []
                for line in response.text.strip().split('\n'):
                    if line.strip():
                        raw_jobs.append(httpx.Response(200, text=line).json())

                # Transform to standard format
                jobs = []
                for job_data in raw_jobs:
                    transformed = self._transform_job_data(job_data)
                    if transformed:
                        jobs.append(transformed)

                logger.info(f"✅ Fetched {len(jobs)} LinkedIn jobs from search URLs")

                return {
                    "success": True,
                    "jobs": jobs,
                    "total_fetched": len(raw_jobs)
                }

        except Exception as e:
            logger.error(f"Error fetching jobs by search URL: {str(e)}")
            return {
                "success": False,
                "error_message": str(e),
                "jobs": []
            }

    def _transform_job_data(self, raw_job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform Bright Data job data to standard format

        Bright Data returns (actual field names):
        {
            "job_title": "Backend Developers (On-site)",
            "company_name": "Choice Talents LTD",
            "job_location": "Lagos, Lagos State, Nigeria",
            "job_summary": "Location: Maryland...",
            "url": "https://linkedin.com/jobs/view/...",
            "job_posted_time": "3 days ago",
            "base_salary": "$120,000 - $180,000" or None,
            "job_employment_type": "Full-time",
            "job_seniority_level": "Mid-Senior level",
            "job_function": "Engineering and Information Technology",
            "job_industries": "Business Consulting and Services",
            "job_num_applicants": 25
        }
        """
        try:
            return {
                "title": raw_job.get("job_title", "Unknown"),
                "company": raw_job.get("company_name", "Unknown"),
                "location": raw_job.get("job_location", ""),
                "description": raw_job.get("job_summary", ""),
                "url": raw_job.get("url", ""),
                "posted_date": raw_job.get("job_posted_time", ""),  # Bright Data returns relative time
                "salary": raw_job.get("base_salary", ""),
                "employment_type": raw_job.get("job_employment_type", ""),
                "seniority_level": raw_job.get("job_seniority_level", ""),
                "job_function": raw_job.get("job_function", ""),
                "industries": raw_job.get("job_industries", ""),
                "applicants_count": raw_job.get("job_num_applicants", "")
            }
        except Exception as e:
            logger.error(f"Error transforming job data: {str(e)}")
            return None
