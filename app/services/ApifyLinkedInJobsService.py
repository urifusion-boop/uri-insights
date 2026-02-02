"""
ApifyLinkedInJobsService - Scrapes LinkedIn Jobs using Apify
Pattern: Same as OpenAIApifyTwitterService but for job postings

This service fetches job postings from LinkedIn Jobs using Apify actors.
"""
import asyncio
from typing import List, Dict, Any, Optional
from apify_client import ApifyClient
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class ApifyLinkedInJobsService:
    """
    Service to fetch job postings from LinkedIn Jobs using Apify
    Pattern: Same as OpenAIApifyTwitterService
    """

    def __init__(self):
        """
        Initialize the service with Apify client
        """
        if not settings.APIFY_API_TOKEN:
            logger.warning("APIFY_API_TOKEN not configured. LinkedIn Jobs scraping will not work.")
            self.apify_client = None
        else:
            self.apify_client = ApifyClient(settings.APIFY_API_TOKEN)

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
        Fetch job postings from LinkedIn Jobs using Apify with intelligent parameter inference

        Args:
            search_query: The search query (e.g., "DevOps Engineer")
            max_jobs: Maximum number of jobs to fetch (default: 15)
            location: Geographic location filter (default: "Worldwide")
            published_at: Time filter (e.g., "Past Week", "Past Month", "Any Time")
            solution_context: Solution description for intelligent inference
            infer_parameters: Enable intelligent parameter inference (default: True)

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
            # Check if client is initialized
            if not self.apify_client:
                return {
                    "success": False,
                    "error_message": "Apify client not initialized. Please configure APIFY_API_TOKEN.",
                    "jobs": []
                }

            # Fetch jobs from Apify with inference
            jobs_result = await self._fetch_jobs_from_apify(
                search_query,
                max_jobs,
                location,
                published_at,
                solution_context,
                infer_parameters
            )

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
            logger.error(f"Error in fetch_job_postings: {str(e)}")
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
        location: str,
        published_at: str = "Past Month",
        solution_context: str = "",
        infer_parameters: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch job postings from Apify using LinkedIn Jobs scraper actor

        Uses curious_coder/linkedin-jobs-search-scraper (primary) with fallback to bebity actor

        Args:
            search_query: Job search query
            max_jobs: Maximum number of jobs to fetch
            location: Geographic location

        Returns:
            Dictionary containing the fetched jobs
        """
        try:
            # PRIMARY ACTOR: curious_coder/linkedin-jobs-search-scraper
            # Docs: https://apify.com/curious_coder/linkedin-jobs-search-scraper
            # Better keyword matching, fresher results, more reliable
            primary_actor_id = "curious_coder/linkedin-jobs-search-scraper"

            # FALLBACK ACTOR: bebity/linkedin-jobs-scraper
            # Used if primary actor fails
            fallback_actor_id = "bebity/linkedin-jobs-scraper"

            # Build LinkedIn job search URL for curious_coder actor
            # This actor requires a pre-built LinkedIn search URL
            search_url = self._build_linkedin_search_url(search_query, location, published_at, infer_parameters, solution_context)

            # Get LinkedIn session cookie from settings and convert to Apify format
            from app.core.config import settings
            linkedin_session_cookie = settings.LINKEDIN_SESSION_COOKIE

            # Convert li_at cookie to Apify JSON format
            linkedin_cookies = None
            if linkedin_session_cookie:
                linkedin_cookies = [
                    {
                        "name": "li_at",
                        "value": linkedin_session_cookie,
                        "domain": ".linkedin.com"
                    }
                ]

            linkedin_user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

            # Configure input for curious_coder actor (URL-based)
            primary_run_input = {
                "searchUrl": search_url,
                "count": max_jobs,
                "scrapeJobDetails": False,  # Faster scraping, we don't need deep details
                "scrapeCompany": False,  # Skip company details for speed
                "scrapeSkills": False,  # Skip skills for speed
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyCountry": "US"  # Use US proxies for consistent results
                }
            }

            # Add cookies if configured
            if linkedin_cookies:
                primary_run_input["cookies"] = linkedin_cookies
                primary_run_input["userAgent"] = linkedin_user_agent
                logger.info("   🔑 Using LinkedIn session cookie for authentication")
            else:
                logger.warning("⚠️ LINKEDIN_SESSION_COOKIE not configured - primary actor will fail, falling back to bebity")
                # Force fallback immediately if no cookies
                raise Exception("LinkedIn session cookie not configured")

            # Fallback input for bebity actor (keyword-based)
            fallback_run_input = {
                "keyword": search_query,
                "maxItems": max_jobs,
                "publishedAt": published_at,
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                }
            }

            if location:
                fallback_run_input["location"] = location

            # Infer parameters for fallback actor
            if infer_parameters:
                from app.services.JobBoardParameterHelper import infer_linkedin_parameters
                inferred = infer_linkedin_parameters(search_query, solution_context)

                if inferred.get("experience_level"):
                    fallback_run_input["experienceLevel"] = inferred["experience_level"]
                if inferred.get("on_site_remote"):
                    fallback_run_input["workType"] = inferred["on_site_remote"]
                if inferred.get("job_type"):
                    fallback_run_input["contractType"] = inferred["job_type"]

            # Try primary actor first, fallback to bebity if it fails
            location_display = location if location else "Worldwide"
            logger.info(f"🔍 Fetching LinkedIn jobs for: '{search_query}' in {location_display}")
            logger.info(f"   Using primary actor: {primary_actor_id}")

            actor_id = primary_actor_id
            run_input = primary_run_input
            used_fallback = False

            try:
                # Run primary actor
                loop = asyncio.get_event_loop()
                run = await loop.run_in_executor(
                    None,
                    lambda: self.apify_client.actor(actor_id).call(run_input=run_input)
                )

                # Check if primary actor succeeded
                if run.get("status") != "SUCCEEDED":
                    raise Exception(f"Primary actor failed with status: {run.get('status', 'Unknown')}")

            except Exception as primary_error:
                logger.warning(f"⚠️ Primary actor ({primary_actor_id}) failed: {str(primary_error)}")
                logger.info(f"   Falling back to: {fallback_actor_id}")

                # Fallback to bebity actor
                actor_id = fallback_actor_id
                run_input = fallback_run_input
                used_fallback = True

                try:
                    loop = asyncio.get_event_loop()
                    run = await loop.run_in_executor(
                        None,
                        lambda: self.apify_client.actor(actor_id).call(run_input=run_input)
                    )

                    if run.get("status") != "SUCCEEDED":
                        error_msg = f"Both actors failed. Fallback actor status: {run.get('status', 'Unknown')}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "error_message": error_msg,
                            "jobs": []
                        }

                except Exception as fallback_error:
                    error_msg = f"Both actors failed. Primary: {str(primary_error)}, Fallback: {str(fallback_error)}"
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
                    logger.debug(f"Sample LinkedIn job item structure: {list(items[0].keys())}")

            except Exception as dataset_error:
                logger.error(f"Error reading dataset: {str(dataset_error)}")
                return {
                    "success": False,
                    "error_message": f"Failed to read results from Apify: {str(dataset_error)}",
                    "jobs": []
                }

            # Process the results (handles both actors' output formats)
            jobs = []
            for item in items[:max_jobs]:
                try:
                    # curious_coder actor returns different field names than bebity
                    # Handle both formats gracefully
                    if not used_fallback:
                        # curious_coder/linkedin-jobs-search-scraper format
                        job_data = {
                            "title": item.get("title") or item.get("jobTitle") or "Unknown Title",
                            "company": item.get("companyName") or item.get("company") or "Unknown Company",
                            "location": item.get("location") or item.get("jobLocation") or location,
                            "description": item.get("description") or item.get("jobDescription") or "",
                            "url": item.get("jobUrl") or item.get("url") or item.get("link") or "",
                            "posted_date": self._parse_posted_date(item.get("postedDate") or item.get("publishedAt")),
                            "salary": item.get("salary") or item.get("salaryRange"),
                            "source": "LinkedIn Jobs"
                        }
                    else:
                        # bebity/linkedin-jobs-scraper format (fallback)
                        job_data = {
                            "title": item.get("title") or item.get("jobTitle") or "Unknown Title",
                            "company": item.get("company") or item.get("companyName") or "Unknown Company",
                            "location": item.get("location") or item.get("jobLocation") or location,
                            "description": item.get("description") or item.get("jobDescription") or "",
                            "url": item.get("url") or item.get("link") or item.get("jobUrl") or "",
                            "posted_date": self._parse_posted_date(item.get("postedDate") or item.get("publishedAt")),
                            "salary": item.get("salary") or item.get("salaryRange"),
                            "source": "LinkedIn Jobs (Fallback)"
                        }

                    # Only add jobs with valid URLs and descriptions
                    if job_data["url"] and job_data["description"]:
                        jobs.append(job_data)
                    else:
                        logger.warning(f"Skipping job with missing URL or description: {job_data['title']}")

                except Exception as item_error:
                    logger.warning(f"Error processing job item: {str(item_error)}")
                    continue

            actor_used = fallback_actor_id if used_fallback else primary_actor_id
            logger.info(f"✅ Successfully fetched {len(jobs)} LinkedIn jobs using {actor_used}")

            return {
                "success": True,
                "jobs": jobs
            }

        except Exception as e:
            logger.error(f"Error fetching jobs from Apify: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": str(e),
                "jobs": []
            }

    def _build_linkedin_search_url(
        self,
        search_query: str,
        location: str,
        published_at: str,
        infer_parameters: bool,
        solution_context: str
    ) -> str:
        """
        Build LinkedIn job search URL with proper filters for curious_coder actor

        Args:
            search_query: Job keyword
            location: Location string
            published_at: Time filter (e.g., "Past Week", "Past Month")
            infer_parameters: Whether to infer additional parameters
            solution_context: Solution context for inference

        Returns:
            Fully formatted LinkedIn job search URL
        """
        import urllib.parse

        # Base LinkedIn jobs search URL
        base_url = "https://www.linkedin.com/jobs/search/?"

        # Build query parameters
        params = {
            "keywords": search_query,
            "location": location or "Worldwide",
            "locationId": "",  # Let LinkedIn auto-detect
            "geoId": "",
        }

        # Add time filter (f_TPR parameter)
        # LinkedIn time filters: r86400 (24h), r604800 (7d), r2592000 (30d), "" (any time)
        time_filter_map = {
            "Past 24 Hours": "r86400",
            "Past Week": "r604800",
            "Past Month": "r2592000",
            "Any Time": "",
            "r86400": "r86400",  # Support direct codes
            "r604800": "r604800",
            "r2592000": "r2592000",
        }
        time_filter = time_filter_map.get(published_at, "")
        if time_filter:
            params["f_TPR"] = time_filter

        # Infer additional parameters if enabled
        if infer_parameters:
            from app.services.JobBoardParameterHelper import infer_linkedin_parameters
            inferred = infer_linkedin_parameters(search_query, solution_context)

            # Experience level filter (f_E parameter)
            # LinkedIn codes: 1=Internship, 2=Entry, 3=Associate, 4=Mid-Senior, 5=Director
            if inferred.get("experience_level"):
                params["f_E"] = inferred["experience_level"]

            # Work type filter (f_WT parameter)
            # LinkedIn codes: 1=On-site, 2=Remote, 3=Hybrid
            if inferred.get("on_site_remote"):
                params["f_WT"] = inferred["on_site_remote"]

            # Job type filter (f_JT parameter)
            # LinkedIn codes: F=Full-time, P=Part-time, C=Contract, T=Temporary, I=Internship
            if inferred.get("job_type"):
                params["f_JT"] = inferred["job_type"]

        # Build URL
        query_string = urllib.parse.urlencode({k: v for k, v in params.items() if v})
        search_url = base_url + query_string

        logger.info(f"   🔗 Built LinkedIn search URL: {search_url[:100]}...")

        return search_url

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
            # Add more formats as needed based on actual data
            from dateutil import parser
            parsed_date = parser.parse(date_str)
            return parsed_date.isoformat()

        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {str(e)}")
            return datetime.now(timezone.utc).isoformat()
