import json
from typing import Any, List, Optional, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.AiRunService import AiRunService
from app.domain.requests.airun_requests import AiRunCreateRequest
from app.core.helpers.assistant_helper import AssistantHelper
from app.repository.AiRunRepository import AiRunRepository
from app.services.EmbeddingService import EmbeddingService
from app.services.HashtagService import HashtagService
from app.services.InstagramService import InstagramService
from app.services.FacebookService import FacebookService
from app.services.ChartService import ChartService
from app.services.LinkedInService import LinkedInService
from app.services.KeywordService import KeywordService


class AiFunctionService:
    @staticmethod
    async def _get_assistant_id(thread) -> Optional[str]:
        """
        Retrieves the assistant ID based on the thread type.
        """
        thread_type = thread.get("thread_type", "")
        return AssistantHelper.get_assistant_id_for_thread_type(thread_type)

    @staticmethod
    async def _trigger_ai_run(
        db: AsyncIOMotorDatabase, thread_id: str, assistant_id: str
    ):
        """
        Initiates an AI run and returns the response.
        """
        run_request = AiRunCreateRequest(assistant_id=assistant_id)
        return await AiRunRepository.create_run(db, thread_id, run_request)

    @staticmethod
    async def _handle_function_calls(
        db: AsyncIOMotorDatabase,
        thread_id: str,
        run_id: str,
        ai_response: dict,
        user_message: Optional[str] = None,
    ):
        """
        Processes function calls required by the AI response.
        """
        required_action = ai_response.get("required_action", {})
        tool_calls = required_action.get("submit_tool_outputs", {}).get(
            "tool_calls", []
        )

        print("AI Tools Call:", tool_calls)

        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            params = json.loads(tool_call["function"]["arguments"])
            print("AI Params:", params)

            response = None
            if function_name == "fetch_cached_hashtag_posts":
                response = await AiFunctionService._execute_ai_hashtag_search(
                    db, params, tool_call, user_message
                )
            if function_name == "fetch_cached_keyword_posts":
                response = await AiFunctionService._execute_ai_keyword_search(
                    db, params, tool_call
                )
            if function_name == "fetch_cached_instagram_posts":
                response = await AiFunctionService._execute_ai_instagram_posts_fetch(
                    db, params, tool_call, user_message
                )
            if function_name == "fetch_cached_facebook_posts":
                response = await AiFunctionService._execute_ai_facebook_posts_fetch(
                    db, params, tool_call, user_message
                )
            if function_name == "fetch_cached_linkedin_posts":
                response = await AiFunctionService._execute_ai_linkedin_posts_fetch(
                    db, params, tool_call, user_message
                )
            if function_name == "generate_chart_data":
                response = await AiFunctionService._execute_ai_generate_chart(
                    db, params, tool_call
                )
            # if function_name == "scrape_web":
            #     response = await AiFunctionService._execute_ai_web_scraping(
            #         params, tool_call
            #     )

            if response:
                await AiRunService.process_function_response(
                    thread_id, run_id, response
                )

    @staticmethod
    async def _execute_ai_keyword_search(
        db: AsyncIOMotorDatabase, params: dict, tool_call: dict
    ) -> Optional[Dict]:
        """
        Executes the AI function call and returns the response with necessary metadata.
        """
        keyword_cache_key = params.get("keyword_cache_key")
        if not keyword_cache_key:
            return None

        post_response = await KeywordService.fetch_cleaned_keyword_posts(
            db, keyword_cache_key
        )

        post_response["responseData"] = post_response.get("responseData", [])[:30]
        print("AI Search Response:", post_response)

        if isinstance(post_response, dict):
            post_response["id"] = tool_call["id"]
        return post_response

    @staticmethod
    async def _execute_ai_hashtag_search(
        db: AsyncIOMotorDatabase,
        params: dict,
        tool_call: dict,
        user_message: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Executes the AI function call and returns the response with necessary metadata.
        """
        hashtag = params.get("hashtag", "")

        print("\nHashtag: ", hashtag)
        print("\nUser message: ", user_message)
        if not hashtag or not user_message:
            return None

        post_response = await EmbeddingService.vector_search_hashtag_tracking_data(
            db, hashtag, user_message
        )

        post_response["responseData"] = post_response.get("responseData", [])[:30]
        print("AI Search Response:", post_response)

        if isinstance(post_response, dict):
            post_response["id"] = tool_call["id"]
        return post_response

    @staticmethod
    async def _execute_ai_instagram_posts_fetch(
        db: AsyncIOMotorDatabase,
        params: dict,
        tool_call: dict,
        user_message: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Executes the AI function call and returns the response with necessary metadata.
        """
        ig_username = params.get("ig_username")
        if not ig_username or not user_message:
            return None

        post_response = await InstagramService.fetch_cached_instagram_posts(
            db, ig_username, user_message
        )
        print("AI Search Response:", post_response)

        if isinstance(post_response, dict):
            post_response["id"] = tool_call["id"]
        return post_response

    @staticmethod
    async def _execute_ai_facebook_posts_fetch(
        db: AsyncIOMotorDatabase,
        params: dict,
        tool_call: dict,
        user_message: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Executes the AI function call for fetching cached Facebook posts.
        """
        facebook_username = params.get("facebook_username")
        if not facebook_username or not user_message:
            return None

        post_response = await FacebookService.fetch_cached_facebook_posts(
            db, facebook_username, user_message
        )
        print("AI Facebook Search Response:", post_response)

        if isinstance(post_response, dict):
            post_response["id"] = tool_call["id"]
        return post_response

    @staticmethod
    async def _execute_ai_linkedin_posts_fetch(
        db: AsyncIOMotorDatabase,
        params: dict,
        tool_call: dict,
        user_message: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Executes the AI function call for fetching cached LinkedIn posts.
        """
        linkedin_username = params.get("linkedin_username")
        if not linkedin_username or not user_message:
            return None

        post_response = await LinkedInService.fetch_cached_linkedin_posts(
            db, linkedin_username, user_message
        )
        print("AI LinkedIn Search Response:", post_response)

        if isinstance(post_response, dict):
            post_response["id"] = tool_call["id"]
        return post_response

    # @staticmethod
    # def _execute_ai_generate_chart(
    #     db: AsyncIOMotorDatabase, params: dict, tool_call: dict
    # ) -> Dict[str, Any]:
    #     """
    #     Generates structured chart data instead of JSX code.
    #     """
    #     chart_type = params.get("chart_type", "bar")  # Default to bar chart
    #     data = params.get("data", [])

    #     # Call the updated ChartService to return structured data
    #     chart_response = ChartService.generate_chart_data(chart_type, data)
    #     if isinstance(chart_response, dict):
    #         chart_response["id"] = tool_call["id"]
    #     return chart_response

    @staticmethod
    async def _execute_ai_generate_chart(
        db: AsyncIOMotorDatabase, params: dict, tool_call: dict
    ) -> Dict[str, Any]:
        chart_type = params.get("chart_type", "bar")  # Default to bar chart
        data = params.get("data", [])

        # Limit the number of data points to reduce token usage
        if len(data) > 10:
            data = data[:10]

        # Call the updated ChartService to return structured data
        chart_response = await ChartService.generate_chart_data(chart_type, data)
        if isinstance(chart_response, dict):
            chart_response["id"] = tool_call["id"]
        return chart_response

    # @staticmethod
    # async def _execute_ai_web_scraping(params: dict, tool_call: dict) -> Dict[str, Any]:
    #     source_urls = params.get("source_urls", [])

    #     print("AI INFERRED URLS: ", source_urls)
