from app.domain.enums.google_enum import TrackerEnum
from app.domain.scrapers.lead_scrapers.LeadDataScraper import LeadDataScraper
from app.services.GoogleService import GoogleService
from app.domain.requests.google_requests import GoogleSearchParams


class GoogleLeadDataScraper(LeadDataScraper):
    async def scrape(self, db, params: GoogleSearchParams) -> list:
        data = await GoogleService.get_multiple_search_data(params, TrackerEnum.LEAD)
        return (data or {}).get("items", [])
