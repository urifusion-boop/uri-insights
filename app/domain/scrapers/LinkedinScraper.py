from app.domain.scrapers.BaseScraper import BaseScraper
from typing import Optional


class LinkedinScraper(BaseScraper):
    def __init__(self, url: str, params: object, headers: Optional[dict] = None):
        super().__init__(url, params, headers)

    async def scrape(self):
        data = await self.fetch_data()
        return data
