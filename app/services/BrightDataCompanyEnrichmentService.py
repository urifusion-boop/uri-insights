"""
BrightDataCompanyEnrichmentService - LinkedIn Company Profile Enrichment
Uses Bright Data REST API: POST /linkedin/companies/collect

This service enriches company monitors with LinkedIn company data:
- Company details (name, about, slogan, description)
- Business information (headquarters, locations, funding)
- Engagement metrics (followers, employees)
- Media assets (logo, banner image)
"""
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class BrightDataCompanyEnrichmentService:
    """
    Service to enrich company profiles using Bright Data REST API
    Endpoint: POST https://api.brightdata.com/linkedin/companies/collect
    """

    def __init__(self):
        """Initialize the service with Bright Data API token"""
        if not hasattr(settings, 'BRIGHTDATA_API_TOKEN') or not settings.BRIGHTDATA_API_TOKEN:
            logger.warning("BRIGHTDATA_API_TOKEN not configured. Company enrichment will not work.")
            self.api_token = None
        else:
            self.api_token = settings.BRIGHTDATA_API_TOKEN
            logger.info("✅ BrightData API token configured for company enrichment")

    async def enrich_company(
        self,
        linkedin_url: str,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Enrich a LinkedIn company profile using Bright Data REST API

        Args:
            linkedin_url: LinkedIn company URL (e.g., "https://www.linkedin.com/company/microsoft/")
            timeout_seconds: Request timeout (default: 60s)

        Returns:
            Dictionary containing enriched company data:
            {
                "success": True,
                "company_id": "1035",
                "name": "Microsoft",
                "about": "...",
                "slogan": "...",
                "description": "...",
                "specialties": ["Cloud Computing", "AI"],
                "organization_type": "Public Company",
                "company_size": "10,001+ employees",
                "industries": ["Software Development"],
                "founded": 1975,
                "country_code": "US",
                "headquarters": "Redmond, Washington, United States",
                "followers": 22000000,
                "employees": 220000,
                "logo": "https://...",
                "company_image": "https://...",
                "url": "https://..."
            }
        """
        try:
            # Check if API token is configured
            if not self.api_token:
                return {
                    "success": False,
                    "error_message": "BrightData API token not configured. Please set BRIGHTDATA_API_TOKEN."
                }

            # Validate LinkedIn company URL
            if not linkedin_url or "linkedin.com/company/" not in linkedin_url:
                return {
                    "success": False,
                    "error_message": "Invalid LinkedIn company URL. Must contain 'linkedin.com/company/'"
                }

            logger.info(f"🔍 Enriching company profile: {linkedin_url}")

            # Call Bright Data REST API
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    "https://api.brightdata.com/linkedin/companies/collect",
                    headers={
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json"
                    },
                    json={"url": linkedin_url}
                )

            # Check response status
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Bright Data API error: {error_msg}")
                return {
                    "success": False,
                    "error_message": error_msg
                }

            # Parse response
            company_data = response.json()

            logger.info(f"✅ Successfully enriched company: {company_data.get('name', 'Unknown')}")

            # Return normalized data
            return {
                "success": True,
                "company_id": company_data.get("id"),
                "name": company_data.get("name"),
                "about": company_data.get("about"),
                "slogan": company_data.get("slogan"),
                "description": company_data.get("description"),
                "specialties": company_data.get("specialties", []),
                "organization_type": company_data.get("organization_type"),
                "company_size": company_data.get("company_size"),
                "industries": company_data.get("industries", []),
                "founded": company_data.get("founded"),
                "country_code": company_data.get("country_code"),
                "headquarters": company_data.get("headquarters"),
                "followers": company_data.get("followers"),
                "employees": company_data.get("employees"),
                "logo": company_data.get("logo"),
                "company_image": company_data.get("image"),
                "url": company_data.get("url"),
                "enriched_at": datetime.now(timezone.utc).isoformat()
            }

        except httpx.TimeoutException:
            logger.error(f"Timeout enriching company: {linkedin_url}")
            return {
                "success": False,
                "error_message": f"Request timed out after {timeout_seconds}s"
            }
        except Exception as e:
            logger.error(f"Error enriching company: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error_message": str(e)
            }
