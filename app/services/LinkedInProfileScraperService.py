"""
LinkedInProfileScraperService - Enriches contacts with email, phone, and profile data
Uses dev_fusion/Linkedin-Profile-Scraper Apify actor

This service enriches Lazarus Protocol contacts by:
1. Extracting verified email addresses
2. Getting phone numbers
3. Collecting work history and current position
4. Gathering profile metadata
"""
import asyncio
from typing import Dict, Any, Optional
from apify_client import ApifyClient
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class LinkedInProfileScraperService:
    """
    Service to enrich LinkedIn profiles using Apify
    Pattern: Same as other Apify services
    """

    def __init__(self):
        """Initialize the service with Apify client"""
        if not settings.APIFY_API_TOKEN:
            logger.warning("APIFY_API_TOKEN not configured. Profile enrichment will not work.")
            self.apify_client = None
        else:
            self.apify_client = ApifyClient(settings.APIFY_API_TOKEN)

    async def enrich_profile(
        self,
        linkedin_url: str,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Enrich a LinkedIn profile with email, phone, and other data

        Args:
            linkedin_url: Full LinkedIn profile URL (e.g., "https://linkedin.com/in/username")
            timeout_seconds: Maximum time to wait for scraping (default: 60s)

        Returns:
            Dictionary containing enriched profile data:
            {
                "success": True,
                "email": "user@example.com",
                "phone": "+1-234-567-8900",
                "profile_data": {
                    "full_name": "John Doe",
                    "headline": "CEO at TechCorp",
                    "location": "San Francisco, CA",
                    "current_company": "TechCorp",
                    "current_position": "CEO",
                    "profile_photo": "https://...",
                    "connections_count": 500,
                    "about": "Bio text...",
                    "work_experience": [...],
                    "education": [...]
                }
            }
        """
        try:
            # Check if client is initialized
            if not self.apify_client:
                return {
                    "success": False,
                    "error_message": "Apify client not initialized. Please configure APIFY_API_TOKEN.",
                    "email": None,
                    "phone": None,
                    "profile_data": {}
                }

            # Validate LinkedIn URL
            if not linkedin_url or "linkedin.com/in/" not in linkedin_url:
                return {
                    "success": False,
                    "error_message": "Invalid LinkedIn profile URL",
                    "email": None,
                    "phone": None,
                    "profile_data": {}
                }

            # Fetch profile from Apify
            profile_result = await self._scrape_profile_from_apify(linkedin_url, timeout_seconds)

            return profile_result

        except Exception as e:
            logger.error(f"Error in enrich_profile: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": f"An error occurred: {str(e)}",
                "email": None,
                "phone": None,
                "profile_data": {}
            }

    async def _scrape_profile_from_apify(
        self,
        linkedin_url: str,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Scrape LinkedIn profile using dev_fusion/Linkedin-Profile-Scraper actor

        Args:
            linkedin_url: LinkedIn profile URL
            timeout_seconds: Timeout for the actor run

        Returns:
            Dictionary containing enriched profile data
        """
        try:
            # LinkedIn Profile Scraper actor from Apify Store
            # Actor: dev_fusion/Linkedin-Profile-Scraper
            # Docs: https://apify.com/dev_fusion/Linkedin-Profile-Scraper
            actor_id = "dev_fusion/Linkedin-Profile-Scraper"

            # Configure the input for the actor
            run_input = {
                "profileUrls": [linkedin_url],  # Array of profile URLs
            }

            # Add LinkedIn session cookie if available (required for authentication)
            if hasattr(settings, 'LINKEDIN_SESSION_COOKIE') and settings.LINKEDIN_SESSION_COOKIE:
                run_input["sessionCookie"] = settings.LINKEDIN_SESSION_COOKIE

            logger.info(f"🔍 Enriching LinkedIn profile: {linkedin_url}")

            # Run actor synchronously in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            run = await loop.run_in_executor(
                None,
                lambda: self.apify_client.actor(actor_id).call(run_input=run_input, timeout_secs=timeout_seconds)
            )

            # Check if the run was successful
            if run.get("status") != "SUCCEEDED":
                error_msg = f"Apify actor run failed with status: {run.get('status', 'Unknown')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error_message": error_msg,
                    "email": None,
                    "phone": None,
                    "profile_data": {}
                }

            # Get the results
            items = []
            try:
                dataset_id = run["defaultDatasetId"]
                for item in self.apify_client.dataset(dataset_id).iterate_items():
                    items.append(item)

                # Log sample structure
                if items:
                    logger.debug(f"Sample profile item structure: {list(items[0].keys())}")

            except Exception as dataset_error:
                logger.error(f"Error reading dataset: {str(dataset_error)}")
                return {
                    "success": False,
                    "error_message": f"Failed to read results from Apify: {str(dataset_error)}",
                    "email": None,
                    "phone": None,
                    "profile_data": {}
                }

            # Process the first item (should only be one profile)
            if not items:
                logger.warning(f"No profile data returned for: {linkedin_url}")
                return {
                    "success": False,
                    "error_message": "No profile data found",
                    "email": None,
                    "phone": None,
                    "profile_data": {}
                }

            profile = items[0]

            # Extract key fields with multiple fallback names
            email = (
                profile.get("email") or
                profile.get("emailAddress") or
                profile.get("mail") or
                None
            )

            phone = (
                profile.get("phone") or
                profile.get("phoneNumber") or
                profile.get("mobile") or
                None
            )

            full_name = (
                profile.get("fullName") or
                profile.get("name") or
                profile.get("full_name") or
                "Unknown"
            )

            headline = (
                profile.get("headline") or
                profile.get("title") or
                profile.get("position") or
                ""
            )

            location = (
                profile.get("location") or
                profile.get("geo") or
                profile.get("address") or
                ""
            )

            profile_photo = (
                profile.get("profilePicture") or
                profile.get("photo") or
                profile.get("photoUrl") or
                profile.get("imgUrl") or
                ""
            )

            # Extract current company and position from headline or experience
            current_company = ""
            current_position = ""

            # Try to parse from headline (e.g., "CEO at TechCorp")
            if headline:
                if " at " in headline:
                    parts = headline.split(" at ")
                    current_position = parts[0].strip()
                    current_company = parts[1].strip() if len(parts) > 1 else ""
                elif " @ " in headline:
                    parts = headline.split(" @ ")
                    current_position = parts[0].strip()
                    current_company = parts[1].strip() if len(parts) > 1 else ""

            # Try to extract from experience
            experience = profile.get("experience") or profile.get("positions") or []
            if experience and len(experience) > 0:
                latest_job = experience[0]
                if not current_company:
                    current_company = latest_job.get("company") or latest_job.get("companyName") or ""
                if not current_position:
                    current_position = latest_job.get("title") or latest_job.get("position") or ""

            # Build enriched profile data
            profile_data = {
                "full_name": full_name,
                "headline": headline,
                "location": location,
                "current_company": current_company,
                "current_position": current_position,
                "profile_photo": profile_photo,
                "connections_count": profile.get("connectionsCount") or profile.get("connections") or 0,
                "about": profile.get("about") or profile.get("summary") or "",
                "work_experience": experience,
                "education": profile.get("education") or profile.get("schools") or [],
                "skills": profile.get("skills") or [],
                "languages": profile.get("languages") or [],
                "certifications": profile.get("certifications") or [],
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"✅ Successfully enriched profile: {full_name}")
            if email:
                logger.info(f"   📧 Email found: {email}")
            if phone:
                logger.info(f"   📱 Phone found: {phone}")

            return {
                "success": True,
                "email": email,
                "phone": phone,
                "profile_data": profile_data
            }

        except Exception as e:
            logger.error(f"Error scraping profile from Apify: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": str(e),
                "email": None,
                "phone": None,
                "profile_data": {}
            }

    async def batch_enrich_profiles(
        self,
        linkedin_urls: list[str],
        max_concurrent: int = 5
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich multiple LinkedIn profiles concurrently

        Args:
            linkedin_urls: List of LinkedIn profile URLs
            max_concurrent: Maximum concurrent requests (default: 5)

        Returns:
            Dictionary mapping URL to enriched profile data
        """
        results = {}

        # Process in batches to avoid overwhelming Apify
        for i in range(0, len(linkedin_urls), max_concurrent):
            batch = linkedin_urls[i:i + max_concurrent]

            # Enrich batch concurrently
            tasks = [self.enrich_profile(url) for url in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Map results
            for url, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results[url] = {
                        "success": False,
                        "error_message": str(result),
                        "email": None,
                        "phone": None,
                        "profile_data": {}
                    }
                else:
                    results[url] = result

        return results
