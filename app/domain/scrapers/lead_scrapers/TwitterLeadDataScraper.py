from typing import Any, Dict
from app.domain.scrapers.lead_scrapers.LeadDataScraper import LeadDataScraper
from app.services.KeywordService import KeywordService
from app.services.XTweetSearchService import XTweetSearchService
from app.domain.requests.twitter_requests import TweetSearchParams


class TwitterLeadDataScraper(LeadDataScraper):
    async def scrape(self, db, params: TweetSearchParams) -> Dict[str, Any]:
        response = await XTweetSearchService.search_recent_tweets(db, params)
        result = response.get("responseData", {})
        cache_key = result.get("cache_key", "")
        prepared_twitter_data = await self.prep_scraped_data_for_leads_gen(
            db, cache_key
        )
        return prepared_twitter_data

    async def prep_scraped_data_for_leads_gen(self, db, cache_key):
        processed_data = (
            (await KeywordService.process_twitter_posts(db, cache_key))
            .get("responseData", {})
            .get("posts_data", [])
        )
        return processed_data
