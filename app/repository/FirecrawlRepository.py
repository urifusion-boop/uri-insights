from firecrawl import FirecrawlApp
from typing import List, Optional, Union
from app.domain.models.post_model import PostModel, ExtractModel
from app.core.config import settings
from urllib.parse import quote_plus
from pydantic import BaseModel
from app.domain.requests.firecrawl_requests import FirecrawlParams
from app.domain.factories.ScraperFactory import ScraperFactory

app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)


class FirecrawlRepository:
    @staticmethod
    async def extract_data(params: FirecrawlParams) -> List[BaseModel]:
        """
        Extracts data (posts, reviews, etc.) from configured domains using Firecrawl scraper.
        """
        try:
            keywords = (
                params.keywords
                if isinstance(params.keywords, list)
                else [params.keywords]
            )
            search_query = quote_plus(" ".join(keywords))

            extracted_data: List[BaseModel] = []

            for domain in params.domains:
                url = f"{domain}/search?q={search_query}&search=Search/*"
                scraper = ScraperFactory.get_scraper("firecrawl", url, params)
                response = scraper.scrape()

                print(f"Extracted Data from {url}: {response}")

                if response.get("success", False):
                    extracted = response.get("data", {}).get(params.extract_field, [])
                    extracted_data.extend(extracted)
                    print(f"Extracted {params.extract_field}: {extracted}")

            return extracted_data
        except Exception as e:
            print(f"[FirecrawlRepository] Error extracting {params.entity} data: {e}")
            return []

    @staticmethod
    async def extract_post_data(
        domains: List[str],
        keywords: Union[List[str], str],
        time_frame: Optional[str] = None,
    ) -> List[PostModel]:
        """
        Extract posts from Firecrawl using the given domains and keywords.
        """
        params = FirecrawlParams(
            domains=domains,
            keywords=keywords,
            entity="post",
            crawl_schema=ExtractModel.model_json_schema(),
            extract_field="posts",
            time_frame=time_frame,
        )
        return await FirecrawlRepository.extract_data(params)

    @staticmethod
    async def extract_reviews_data(
        domains: List[str],
        keywords: Union[List[str], str],
        time_frame: Optional[str] = None,
    ) -> List[PostModel]:
        """
        Extract reviews from Firecrawl using the given domains and keywords.
        """
        params = FirecrawlParams(
            domains=domains,
            keywords=keywords,
            entity="review",
            crawl_schema=ExtractModel.model_json_schema(),
            extract_field="reviews",
            time_frame=time_frame,
        )
        return await FirecrawlRepository.extract_data(params)
