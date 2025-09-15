import asyncio
from concurrent.futures import ProcessPoolExecutor
import json
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from datetime import timedelta
import requests
from http import HTTPStatus
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.helpers.reddit_helper import RedditHelper
from app.domain.factories.AdapterFactory import AdapterFactory
from app.domain.responses.uri_response import UriResponse
from app.domain.factories.ScraperFactory import ScraperFactory
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.requests.reddit_requests import (
    RedditCommentsSearchParams,
    RedditSearchParams,
)
from app.core.managers.ProcessPoolManager import process_pool_manager
from concurrent.futures import as_completed


class RedditService:
    BASE_URL = "https://www.reddit.com/r/all/comments/.json"
    CACHE_TTL = timedelta(hours=1)  # Cache for 1 hour

    @staticmethod
    async def get_comments(
        db: AsyncIOMotorDatabase,
        limit: int = 100,
        params: RedditCommentsSearchParams = RedditCommentsSearchParams(),
    ) -> Dict[str, Any]:
        """
        Fetch comments from the Reddit API with optional filtering and adapt them to the web result structure.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param limit: The number of comments to fetch.
        :params: The search parameters.
        :return: Filtered and transformed comments in the desired structure.
        """
        full_url = f"{RedditService.BASE_URL}?limit={limit}"
        print("Full Reddit URL : ", full_url)

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(full_url)

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("comments", cached_data)

        # Make request
        response = requests.get(full_url)

        print("Reddit Response : ", response)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("message", "Failed to fetch comments."),
            )

        result = response.json()
        filtered_comments = await RedditService.filter_comments(
            result.get("data", {}).get("children", []), params.includes, params.excludes
        )

        transformed_comments = await RedditService.transform_comments(filtered_comments)

        # Cache the transformed response
        await CacheRepository.set_cache(
            db=db,
            cache_key=cache_key,
            data=transformed_comments,
            ttl=RedditService.CACHE_TTL,
        )

        return UriResponse.get_single_data_response("comments", transformed_comments)

    @staticmethod
    async def filter_comments(
        comments: List[Dict[str, Any]],
        includes: Optional[List[str]],
        excludes: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """
        Filter comments based on included and excluded keywords.
        :param comments: List of comment dictionaries to filter.
        :param includes: List of keywords that must be included in comments.
        :param excludes: List of keywords that must not be included in comments.
        :return: Filtered list of comments.
        """
        filtered = []

        for comment in comments:
            body = comment.get("data", {}).get("body", "").lower()
            if includes and not any(word.lower() in body for word in includes):
                continue  # Skip comments that don't include required words
            if excludes and any(word.lower() in body for word in excludes):
                continue  # Skip comments that include excluded words
            filtered.append(comment)

        return filtered

    @staticmethod
    async def transform_comments(
        comments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Transform Reddit comments to match the desired web result structure.
        :param comments: List of Reddit comments.
        :return: Transformed comments.
        """
        transformed = []

        for comment in comments:
            data = comment.get("data", {})
            permalink = data.get("link_permalink", "")
            parsed_url = urlparse(permalink)
            domain = parsed_url.netloc

            transformed.append(
                {
                    "kind": "customsearch#result",
                    "title": data.get("link_title", ""),
                    "htmlTitle": data.get("link_title", ""),
                    "link": permalink,
                    "displayLink": domain,
                    "snippet": data.get("body", "")[:200],
                    "htmlSnippet": data.get("body", "")[
                        :200
                    ],  # Use HTML-escaped version if needed
                    "formattedUrl": permalink,
                    "htmlFormattedUrl": permalink,
                    "pagemap": {
                        "cse_thumbnail": [
                            {
                                "src": data.get("link_url", ""),
                                "width": "137",
                                "height": "105",
                            }
                        ],
                        "metatags": [
                            {
                                "og:image": data.get("link_url", ""),
                                "og:title": data.get("link_title", ""),
                                "og:url": permalink,
                                "author": data.get("author", ""),
                                "og:description": data.get("body", "")[:200],
                            }
                        ],
                    },
                }
            )

        return transformed

    @staticmethod
    async def get_multiple_search_data(params: RedditSearchParams) -> Dict[str, Any]:
        url = "https://oauth.reddit.com/r/all/search.json"

        headers = {
            "Authorization": "",
        }

        user_agent = RedditHelper.generate_user_agent()
        print("Reddit user agent: ", user_agent)
        if user_agent:
            headers["User-Agent"] = user_agent

        all_items = []
        max_loops = params.max_pages
        loop_count = 1
        # Fetch first response
        try:
            scraper = ScraperFactory.get_scraper("reddit", url, params, headers)
            response = scraper.fetch_data()
            response_data, after, count = RedditService.__get_listing_response_info(
                response
            )
            all_items.extend(response_data.get("data", {}).get("children"))
            print("Loop count VS max_loops: ", loop_count, max_loops)
            while after and (loop_count < max_loops):
                params.after = after
                params.count = count

                response = scraper.fetch_data()
                response_data, after, count = RedditService.__get_listing_response_info(
                    response
                )
                all_items.extend(response_data.get("data", {}).get("children"))
                loop_count += 1
            print("Reddit search iteration: ", loop_count)
            response_data["data"]["children"] = all_items
            return response_data
        except Exception as e:
            print(f"Exception occurred in scraping leads data: {e}")
            return UriResponse.error_response(str(e))

    @staticmethod
    async def __get_listing_response_info(response):
        if response.status_code == HTTPStatus.OK:
            response_data = response.json()
            after = response_data.get("data", {}).get("after")
            count = response_data.get("data", {}).get("dist")
            return response_data, after, count
        print(
            f"Error in getting search data: {response.json or response.text} {response.status_code}"
        )
        raise HTTPException(response.status_code)

    @staticmethod
    async def batch_construct_reddit_search_params_from_business_info(
        business_info_list: List[dict],
    ) -> List[Dict[str, Any]]:
        """
        Batch construct RedditSearchParams from business information.
        """
        executor = process_pool_manager.get_executor()
        futures = [
            executor.submit(
                RedditHelper.construct_reddit_search_params_from_business_info,
                business_info,
            )
            for business_info in business_info_list
        ]
        return [future.result() for future in futures]

    @staticmethod
    async def scrape_reddit_for_leads(
        db: AsyncIOMotorDatabase, data: Dict[str, Any]
    ) -> Optional[dict]:
        params = data.get("params", {})

        if not params:
            print("Reddit params for scraping lead data not found")
            return None

        cache_key = CacheHelper.generate_cache_key(
            json.dumps(params.dict(exclude_none=True))
        )
        cached_response = await CacheRepository.get_cache(db, cache_key)
        if cached_response:
            result = cached_response
        else:
            result = await RedditService.get_multiple_search_data(params)
            await CacheRepository.set_cache(db, cache_key, result)

        result_dict = {
            "user_id": data.get("user_id"),
            "result": result.get("data", {}).get("children", []),
            "platform": "reddit",
        }
        await asyncio.sleep(1)
        return result_dict

    @staticmethod
    async def batch_scrape_reddit_for_leads(
        db: AsyncIOMotorDatabase, batch: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        print("Batch scraping reddit for leads")
        tasks = [RedditService.scrape_reddit_for_leads(db, data) for data in batch]

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
            result = []
            if data:
                for item in data:
                    adapted_item = AdapterFactory.get_adapter("reddit", item).to_lead()
                    if adapted_item:
                        result.append(adapted_item)
                scraped_data["result"] = result
                if result:
                    return scraped_data
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
                executor.submit(RedditService.adapt_scraped_data_for_leads, data)
                for data in scraped_data
            ]
            for future in as_completed(futures):
                result.append(future.result())
        except Exception as e:
            print(
                f"Exception occurred in batch adapt reddit scraped data for leads: {e}"
            )
        return result
