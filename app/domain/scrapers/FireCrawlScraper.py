from typing import Optional
from app.domain.requests.firecrawl_requests import FirecrawlParams
from app.domain.scrapers.BaseScraper import BaseScraper
from app.core.config import settings
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)


class FireCrawlScraper(BaseScraper):
    def __init__(
        self,
        url: str,
        params: Optional[FirecrawlParams] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(url, params, headers)

    async def scrape(self):
        words = (
            self.params.keywords
            if isinstance(self.params.keywords, list)
            else [self.params.keywords]
        )
        data = app.extract(
            [self.url],
            {
                "prompt": f"""
                Extract the username, profile link, comment and timestamp from each {self.params.entity} for {" ".join(words)}.
                Only return data within the time frame of {self.params.time_frame}.
                """,
                "schema": self.params.crawl_schema,
            },
        )
        return data
