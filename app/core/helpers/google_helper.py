from datetime import datetime
import json
from typing import Optional
from app.domain.requests.google_requests import GoogleSearchParams
from app.core.helpers.text_helper import TextHelper
from app.services.AIService import AIService


class GoogleHelper:
    @staticmethod
    def construct_google_search_params_from_business_info(
        business_info: dict, group: int = 1
    ) -> GoogleSearchParams:
        """
        Construct GoogleSearchParams from business information.

        Args:
            business_info (dict): Dictionary containing business information.
        """
        keywords: list = business_info.get("keywords", [])
        competitors: list = business_info.get("competitors", [])
        keywords.extend(competitors)
        params_dict = {
            **GoogleHelper.separate_words_and_phrases(keywords),
            "date_restrict": GoogleHelper.get_date_restrict_from_last_scraped_date(
                business_info.get("settings", {}).get("last_scraped_date")
            ),
            "max_search_iteration_count": 1,
            "num": 50,
        }

        if group == 1:
            params_dict["platforms"] = [
                "linkedin.com",
                "facebook.com",
                "twitter.com",
                "instagram.com",
                "tiktok.com",
            ]
        elif group == 2:
            params_dict["platforms"] = [
                "threads.net",
                "medium.com",
                "nairaland.com",
                "reddit.com",
            ]

        return GoogleSearchParams(**params_dict)

    @staticmethod
    def get_timestamp_from_search(item: dict):
        # Extract timestamp fields or use fallback snippet if not available
        metatags = item.get("pagemap", {}).get("metatags", [])
        if metatags:
            metatag_item = metatags[0]
            timestamp = metatag_item.get(
                "article:published_time", None
            ) or metatag_item.get("article:modified_time", None)
            if not timestamp:
                timestamp = item.get("snippet", "")
            timestamp = (
                TextHelper.extract_timestamp_from_text(timestamp)
                or TextHelper.extract_timestamp_from_date_text(timestamp)
                or TextHelper.extract_timestamp_from_relative_date_text(timestamp)
            )
            if timestamp:
                return timestamp
        return None

    @staticmethod
    def get_date_restrict_from_last_scraped_date(
        last_scraped_date: Optional[datetime],
    ) -> str:
        """
        Get date restrict from last scraped date.
        """
        if not last_scraped_date:
            return "d30"
        try:
            time_difference = (datetime.utcnow() - last_scraped_date).days
            date_restrict_string = f"d{1 if time_difference == 0 else time_difference}"
            return date_restrict_string
        except Exception as e:
            print(f"Error getting date restrict from last scraped date: {e}")
            return "d30"

    @staticmethod
    def separate_words_and_phrases(strings_list):
        categorized_dict = {
            "includes": [],  # Single-word strings
            "phrases": [],  # Multi-word strings
        }

        for string in strings_list:
            if " " in string.strip():
                categorized_dict["phrases"].append(string)
            else:
                categorized_dict["includes"].append(string)

        return categorized_dict

    @staticmethod
    async def construct_google_search_params_with_ai(
        lead_form_info: dict,
    ) -> GoogleSearchParams:
        """
        Use AI to generate google search params
        """
        prompt = f"""
            You are a search intelligence assistant.
            Based on the following lead form input, generate a set of Google search parameters that conform to the GoogleSearchParams schema...
            The goal is to retrieve highly relevant, recent, and filtered Google search results that align with the user's intent.

            Instructions:
            1. Extract key concepts and goals from the lead form.
            2. Use the keywords, description, and other applicable fields (form_type, location, target_audience, hiring_role, etc.) to inform the search query.
            3. Map the extracted information to the following fields in the search parameters:
                includes: Core search keywords.
                phrases: Exact phrases from description or file content.
                locations: If a location or site context is mentioned (e.g., site:linkedin.com, or a region).
                languages: Default to English unless specified.
                gl and cr: Infer geolocation from location field.
                safe: Set to "active" by default.
                sort: "date" to prioritize recent results.
                num: Use 10.
                filter: 1 to filter duplicate results.
                date_restrict: Default to "d30" unless specified.
            4. Leave fields blank or None if not applicable.

            Lead Form:
            {json.dumps(lead_form_info)}
        """

        ai_model = AIService.build_ai_model([AIService.construct_user_prompt(prompt)])

        ai_full_response = await AIService.structured_chat_completion(
            ai_model, GoogleSearchParams
        )

        constructed_ai_params = AIService.extract_ai_result(ai_full_response)

        return constructed_ai_params
