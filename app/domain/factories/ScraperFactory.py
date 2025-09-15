from typing import Optional
from app.domain.scrapers.GoogleScraper import GoogleScraper
from app.domain.scrapers.RedditScraper import RedditScraper
from app.domain.scrapers.LinkedinScraper import LinkedinScraper
from app.domain.scrapers.FireCrawlScraper import FireCrawlScraper


class ScraperFactory:
    scrapers = {
        "google": GoogleScraper,
        "reddit": RedditScraper,
        "linkedin": LinkedinScraper,
        "firecrawl": FireCrawlScraper,
    }

    @staticmethod
    def get_scraper(
        scraper_type: str,
        url: str,
        params: Optional[object] = None,
        headers: Optional[dict] = None,
    ):
        return ScraperFactory.scrapers.get(scraper_type, GoogleScraper)(
            url, params, headers
        )
