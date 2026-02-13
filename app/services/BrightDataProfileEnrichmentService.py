"""
BrightDataProfileEnrichmentService - Enriches LinkedIn contacts with email, phone, and profile data
Uses Bright Data Python SDK (brightdata-sdk package)

This service enriches Lazarus Protocol contacts by:
1. Extracting verified email addresses
2. Getting phone numbers
3. Collecting work history and current position
4. Gathering profile metadata (photo, headline, location, etc.)

Replaces: LinkedInProfileScraperService (Apify-based)
"""
import asyncio
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class BrightDataProfileEnrichmentService:
    """
    Service to enrich LinkedIn profiles using Bright Data Python SDK
    Uses: client.scrape.linkedin.profiles()
    """

    def __init__(self):
        """Initialize the service with Bright Data client"""
        try:
            from brightdata import BrightDataClient

            if not hasattr(settings, 'BRIGHTDATA_API_TOKEN') or not settings.BRIGHTDATA_API_TOKEN:
                logger.warning("BRIGHTDATA_API_TOKEN not configured. Profile enrichment will not work.")
                self.client = None
            else:
                # Initialize Bright Data client
                # SDK auto-loads from BRIGHTDATA_API_TOKEN env var or can be passed directly
                self.client = BrightDataClient(token=settings.BRIGHTDATA_API_TOKEN)
                logger.info("✅ BrightData client initialized successfully")
        except ImportError:
            logger.error("brightdata-sdk package not installed. Run: pip install brightdata-sdk")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize BrightData client: {str(e)}")
            self.client = None

    async def enrich_profile(
        self,
        linkedin_url: str,
        timeout_seconds: int = 90
    ) -> Dict[str, Any]:
        """
        Enrich a LinkedIn profile with email, phone, and other data using Bright Data

        Args:
            linkedin_url: Full LinkedIn profile URL (e.g., "https://linkedin.com/in/username")
            timeout_seconds: Maximum time to wait for scraping (default: 90s)

        Returns:
            Dictionary containing enriched profile data:
            {
                "success": True,
                "profile": {
                    "email": "user@example.com",
                    "phone": "+1-234-567-8900",
                    "full_name": "John Doe",
                    "headline": "CEO at TechCorp",
                    "location": "San Francisco, CA",
                    "current_company": "TechCorp",
                    "current_position": "CEO",
                    "profile_photo_url": "https://...",
                    "connections_count": 500,
                    "about": "Bio text...",
                    "work_experience": [...],
                    "education": [...],
                    "skills": [...],
                    "languages": [...],
                    "certifications": [...]
                }
            }
        """
        try:
            # Check if client is initialized
            if not self.client:
                return {
                    "success": False,
                    "error_message": "BrightData client not initialized. Please configure BRIGHTDATA_API_TOKEN and install brightdata-sdk.",
                    "profile": {}
                }

            # Validate LinkedIn URL
            if not linkedin_url or "linkedin.com/in/" not in linkedin_url:
                return {
                    "success": False,
                    "error_message": "Invalid LinkedIn profile URL. Must contain 'linkedin.com/in/'",
                    "profile": {}
                }

            logger.info(f"🔍 Enriching LinkedIn profile via Bright Data: {linkedin_url}")

            # Fetch profile from Bright Data
            profile_result = await self._scrape_profile_from_brightdata(linkedin_url, timeout_seconds)

            return profile_result

        except Exception as e:
            logger.error(f"Error in enrich_profile: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": f"An error occurred: {str(e)}",
                "profile": {}
            }

    async def _scrape_profile_from_brightdata(
        self,
        linkedin_url: str,
        timeout_seconds: int = 90
    ) -> Dict[str, Any]:
        """
        Scrape LinkedIn profile using Bright Data SDK

        Args:
            linkedin_url: LinkedIn profile URL
            timeout_seconds: Timeout for the request

        Returns:
            Dictionary containing enriched profile data
        """
        try:
            # Call Bright Data SDK (async method)
            result = await self.client.scrape.linkedin.profiles(
                url=linkedin_url,
                timeout=timeout_seconds
            )

            # Check if request was successful
            if not result.success:
                error_msg = getattr(result, 'error_message', 'Unknown error from Bright Data')
                logger.error(f"Bright Data request failed: {error_msg}")
                return {
                    "success": False,
                    "error_message": error_msg,
                    "profile": {}
                }

            # Extract profile data from result
            if not result.data or len(result.data) == 0:
                logger.warning(f"No profile data returned for: {linkedin_url}")
                return {
                    "success": False,
                    "error_message": "No profile data found",
                    "profile": {}
                }

            # Get first profile (should be the only one for single URL)
            raw_profile = result.data[0]

            # Log sample structure for debugging
            logger.debug(f"Bright Data profile keys: {list(raw_profile.keys())}")

            # Parse and normalize profile data
            profile = self._parse_profile_data(raw_profile)

            logger.info(f"✅ Successfully enriched profile: {profile['full_name']}")
            if profile.get('email'):
                logger.info(f"   📧 Email found: {profile['email']}")
            if profile.get('phone'):
                logger.info(f"   📱 Phone found: {profile['phone']}")

            return {
                "success": True,
                "profile": profile
            }

        except Exception as e:
            logger.error(f"Error scraping profile from Bright Data: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": str(e),
                "profile": {}
            }

    def _parse_profile_data(self, raw_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and normalize profile data from Bright Data response
        Handles field name variations and extracts structured data

        Args:
            raw_profile: Raw profile data from Bright Data

        Returns:
            Normalized profile dictionary
        """
        # Extract basic fields with fallbacks for different field names
        email = (
            raw_profile.get("email") or
            raw_profile.get("emailAddress") or
            raw_profile.get("mail") or
            raw_profile.get("contact_email") or
            None
        )

        phone = (
            raw_profile.get("phone") or
            raw_profile.get("phoneNumber") or
            raw_profile.get("mobile") or
            raw_profile.get("contact_phone") or
            None
        )

        full_name = (
            raw_profile.get("fullName") or
            raw_profile.get("name") or
            raw_profile.get("full_name") or
            raw_profile.get("firstName", "") + " " + raw_profile.get("lastName", "")
        ).strip() or "Unknown"

        headline = (
            raw_profile.get("headline") or
            raw_profile.get("title") or
            raw_profile.get("position") or
            raw_profile.get("currentPosition") or
            ""
        )

        location = (
            raw_profile.get("location") or
            raw_profile.get("geo") or
            raw_profile.get("address") or
            raw_profile.get("city") or
            ""
        )

        profile_photo_url = (
            raw_profile.get("profilePicture") or
            raw_profile.get("photo") or
            raw_profile.get("photoUrl") or
            raw_profile.get("imgUrl") or
            raw_profile.get("image") or
            raw_profile.get("avatar") or
            ""
        )

        about = (
            raw_profile.get("about") or
            raw_profile.get("summary") or
            raw_profile.get("bio") or
            raw_profile.get("description") or
            ""
        )

        connections_count = (
            raw_profile.get("connectionsCount") or
            raw_profile.get("connections") or
            raw_profile.get("connectionCount") or
            raw_profile.get("followers") or
            0
        )

        # Extract current company and position
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

        # Extract work experience
        experience = (
            raw_profile.get("experience") or
            raw_profile.get("positions") or
            raw_profile.get("workExperience") or
            raw_profile.get("work_experience") or
            []
        )

        # Try to extract current role from experience if not found in headline
        if experience and isinstance(experience, list) and len(experience) > 0:
            latest_job = experience[0]
            if not current_company:
                current_company = (
                    latest_job.get("company") or
                    latest_job.get("companyName") or
                    latest_job.get("organization") or
                    ""
                )
            if not current_position:
                current_position = (
                    latest_job.get("title") or
                    latest_job.get("position") or
                    latest_job.get("role") or
                    ""
                )

        # Extract education
        education = (
            raw_profile.get("education") or
            raw_profile.get("schools") or
            raw_profile.get("educationHistory") or
            []
        )

        # Extract skills
        skills = (
            raw_profile.get("skills") or
            raw_profile.get("skillsList") or
            []
        )

        # Extract languages
        languages = (
            raw_profile.get("languages") or
            raw_profile.get("languagesList") or
            []
        )

        # Extract certifications
        certifications = (
            raw_profile.get("certifications") or
            raw_profile.get("certificates") or
            raw_profile.get("certificationsList") or
            []
        )

        # Build normalized profile data
        return {
            "email": email,
            "phone": phone,
            "full_name": full_name,
            "headline": headline,
            "location": location,
            "current_company": current_company,
            "current_position": current_position,
            "profile_photo_url": profile_photo_url,
            "connections_count": connections_count,
            "about": about,
            "work_experience": experience,
            "education": education,
            "skills": skills,
            "languages": languages,
            "certifications": certifications,
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }

    async def batch_enrich_profiles(
        self,
        linkedin_urls: List[str],
        timeout_seconds: int = 180
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich multiple LinkedIn profiles in batch using Bright Data

        This uses Bright Data's built-in batch processing for better performance
        compared to running individual requests concurrently.

        Args:
            linkedin_urls: List of LinkedIn profile URLs
            timeout_seconds: Timeout for the entire batch request (default: 180s)

        Returns:
            Dictionary mapping URL to enriched profile data:
            {
                "https://linkedin.com/in/user1": {"success": True, "profile": {...}},
                "https://linkedin.com/in/user2": {"success": True, "profile": {...}}
            }
        """
        try:
            if not self.client:
                return {
                    url: {
                        "success": False,
                        "error_message": "BrightData client not initialized",
                        "profile": {}
                    }
                    for url in linkedin_urls
                }

            if not linkedin_urls:
                return {}

            # Filter valid LinkedIn URLs
            valid_urls = [
                url for url in linkedin_urls
                if url and "linkedin.com/in/" in url
            ]

            if not valid_urls:
                return {
                    url: {
                        "success": False,
                        "error_message": "Invalid LinkedIn URL",
                        "profile": {}
                    }
                    for url in linkedin_urls
                }

            logger.info(f"🔍 Batch enriching {len(valid_urls)} LinkedIn profiles via Bright Data")

            # Call Bright Data SDK (async method)
            result = await self.client.scrape.linkedin.profiles(
                url=valid_urls,  # SDK accepts list of URLs
                timeout=timeout_seconds
            )

            # Process results
            results = {}

            if not result.success:
                error_msg = getattr(result, 'error_message', 'Batch request failed')
                logger.error(f"Bright Data batch request failed: {error_msg}")
                return {
                    url: {
                        "success": False,
                        "error_message": error_msg,
                        "profile": {}
                    }
                    for url in valid_urls
                }

            # Map results to URLs
            for i, url in enumerate(valid_urls):
                try:
                    if i < len(result.data):
                        raw_profile = result.data[i]
                        profile = self._parse_profile_data(raw_profile)
                        results[url] = {
                            "success": True,
                            "profile": profile
                        }
                        logger.info(f"✅ Enriched: {profile['full_name']}")
                    else:
                        results[url] = {
                            "success": False,
                            "error_message": "No data returned for this URL",
                            "profile": {}
                        }
                except Exception as e:
                    logger.error(f"Error processing profile {url}: {str(e)}")
                    results[url] = {
                        "success": False,
                        "error_message": str(e),
                        "profile": {}
                    }

            logger.info(f"✅ Batch enrichment completed: {len(results)} profiles processed")
            return results

        except Exception as e:
            logger.error(f"Error in batch_enrich_profiles: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                url: {
                    "success": False,
                    "error_message": f"Batch processing error: {str(e)}",
                    "profile": {}
                }
                for url in linkedin_urls
            }
