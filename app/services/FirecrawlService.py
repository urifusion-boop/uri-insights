import asyncio
import json
from typing import Any, Dict, List, Optional

from app.core.helpers.cache_helper import CacheHelper
from app.core.helpers.firecrawl_helper import FirecrawlHelper
from app.core.managers.ProcessPoolManager import process_pool_manager
from app.domain.requests.firecrawl_requests import FirecrawlParams
from app.repository.CacheRepository import CacheRepository
from app.repository.FirecrawlRepository import FirecrawlRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

from concurrent.futures import as_completed


class FirecrawlService:
    @staticmethod
    async def batch_process_firecrawl_input(batch: List[dict]) -> Optional[List[dict]]:
        executor = process_pool_manager.get_executor()
        futures = [
            executor.submit(FirecrawlHelper.construct_firecrawl_input, business_info)
            for business_info in batch
        ]
        return [future.result() for future in futures]

    @staticmethod
    async def scrape_firecrawl_for_leads(
        db: AsyncIOMotorDatabase, data: Dict[str, Any]
    ) -> Optional[dict]:
        params: Optional[FirecrawlParams] = data.get("params", {})
        if not params or params == {}:
            print("Firecrawl params not found")
            return None
        cache_key = CacheHelper.generate_cache_key(params)
        cached_response = await CacheRepository.get_cache(db, cache_key)

        if cached_response:
            result = cached_response
        else:
            domains = params.get("domains")
            keywords = params.get("keywords")
            time_frame = params.get("time_frame")
            tasks = [
                FirecrawlRepository.extract_post_data(domains, keywords, time_frame),
                FirecrawlRepository.extract_reviews_data(domains, keywords, time_frame),
            ]

            post_result, reviews_result = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            result = post_result.extend(reviews_result)

            await CacheRepository.set_cache(db, cache_key, result)

        result_dict = {
            "user_id": data.get("user_id"),
            "result": result,
            "platform": "firecrawl",
        }
        await asyncio.sleep(4)
        return result_dict

    @staticmethod
    async def batch_scrape_firecrawl_for_leads(
        db: AsyncIOMotorDatabase, batch: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Process batch of business information in parallel using asyncio
        """
        print("Batch scraping firecrawl for leads")
        tasks = [
            FirecrawlService.scrape_firecrawl_for_leads(db, data) for data in batch
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def adapt_scraped_data_for_leads(
        scraped_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Adapt scraped data for leads
        """
        if scraped_data:
            data = scraped_data.get("result")
            if data:
                return data
        return None

    @staticmethod
    async def batch_adapt_scraped_data_for_leads(
        scraped_data: List[Dict[str, Any]]
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Batch adapt scraped data for leads
        """
        result = []
        try:
            executor = process_pool_manager.get_executor()
            futures = [
                executor.submit(
                    FirecrawlService.adapt_scraped_data_for_leads, scraped_data
                )
                for scraped_data in scraped_data
            ]
            for future in as_completed(futures):
                result.append(future.result())
        except Exception as e:
            print(f"Exception occurred in batch adapt firecrawl data for leads: {e}")
        return result
