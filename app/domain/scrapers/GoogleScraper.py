from typing import Optional
from app.domain.scrapers.BaseScraper import BaseScraper
from app.domain.requests.google_requests import GoogleSearchParams


class GoogleScraper(BaseScraper):
    def __init__(
        self,
        url: str,
        params: Optional[GoogleSearchParams] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(url, params, headers)

    def scrape(self):
        data = self.fetch_data()
        return data
