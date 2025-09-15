from app.domain.scrapers.BaseScraper import BaseScraper
from app.domain.requests.reddit_requests import RedditSearchParams
from typing import Optional


class RedditScraper(BaseScraper):
    def __init__(
        self, url: str, params: RedditSearchParams, headers: Optional[dict] = None
    ):
        super().__init__(url, params, headers)

    async def scrape(self):
        data = await self.fetch_data()
        return data
