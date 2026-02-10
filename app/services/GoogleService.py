import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse
from google.cloud import language_v1
from google.oauth2 import service_account
import requests
from app.core.config import settings
from typing import Any, Dict, List
from app.domain.enums.google_enum import TrackerEnum
from app.domain.requests.google_requests import GoogleSearchParams
from app.core.helpers.text_helper import TextHelper
import os

from app.domain.factories.ScraperFactory import ScraperFactory
from urllib.parse import quote_plus

from app.services.AIService import AIService


class GoogleService:
    @staticmethod
    async def analyze_sentimentV1(text: str) -> Any:
        """
        Perform sentiment analysis using Google Cloud Natural Language API.
        The service account JSON is referenced from the environment variable or path.
        """
        credentials_path = settings.GOOGLE_APPLICATION_CREDENTIALS

        # Load the credentials explicitly if the path is provided
        if os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            client = language_v1.LanguageServiceClient(credentials=credentials)
        else:
            raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

        # Construct the document
        document = language_v1.Document(
            content=text, type_=language_v1.Document.Type.PLAIN_TEXT
        )

        # Perform sentiment analysis
        try:
            sentiment = client.analyze_sentiment(document=document).document_sentiment
        except Exception as e:
            return {"error": str(e)}

        # Construct a response
        response_data = {
            "text": text,
            "score": sentiment.score,  # Sentiment score ranges between -1.0 (negative) and 1.0 (positive)
            "magnitude": sentiment.magnitude,  # Magnitude indicates strength of sentiment
        }
        return response_data

    @staticmethod
    def analyze_sentiment(text: str) -> dict:
        """
        Perform sentiment analysis on a given text using Google Cloud Natural Language API.

        Args:
            text (str): Text to analyze for sentiment.

        Returns:
            dict: Contains the sentiment score, magnitude, and sentiment type.
        """
        client = GoogleService.get_nlp_client()
        document = language_v1.Document(
            content=text, type_=language_v1.Document.Type.PLAIN_TEXT
        )

        try:
            sentiment = client.analyze_sentiment(document=document).document_sentiment
        except Exception as e:
            return {"error": str(e)}

        return {
            "text": text,
            "score": sentiment.score,
            "magnitude": sentiment.magnitude,
            "sentiment": (
                "positive"
                if sentiment.score > 0
                else "negative" if sentiment.score < -0.2 else "neutral"
            ),
        }

    @staticmethod
    async def get_search_data(params: GoogleSearchParams) -> Any:
        query = await GoogleService.construct_keyword_tracking_query_url(params)
        # Construct the full API URL with the dynamic query
        base_url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={settings.GOOGLE_CUSTOM_SEARCH_ENGINE_API_KEY}&cx={settings.URI_SEARCH_ENGINE_ID}"
        response = requests.get(base_url)
        return response

    @staticmethod
    async def extract_urls(data: Dict):
        urls = []
        for item in data["items"]:
            urls.append(item["link"])
        return urls

    @staticmethod
    async def get_multiple_search_data(
        params: GoogleSearchParams, tracker: TrackerEnum = TrackerEnum.KEYWORD
    ) -> Any:
        """
        Retrieve multiple pages of search data from the Google Custom Search API,
        limiting to a maximum of 5 loops to avoid excessive API calls.

        Args:
            params (GoogleSearchParams): Parameters for the search query.

        Returns:
            dict: Aggregated search results containing all retrieved items.
        """
        if tracker == TrackerEnum.LEAD:
            query = await GoogleService.construct_lead_tracking_query_url(params)
        else:
            query = await GoogleService.construct_keyword_tracking_query_url(params)

        # Construct the full API URL with the dynamic query
        base_url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={settings.GOOGLE_CUSTOM_SEARCH_ENGINE_API_KEY}&cx={settings.URI_SEARCH_ENGINE_ID}"

        # Initialize variables
        start_index = params.start
        max_results_per_page = 10
        all_items = []
        max_loops = params.max_search_iteration_count  # Limit the number of loops to 5
        loop_count = 0

        # Make the initial request and check totalResults
        url = f"{base_url}&start={start_index}&num={max_results_per_page}"
        print(f"[GOOGLE SEARCH] 🔍 Fetching URL: {url[:200]}...")
        response = ScraperFactory.get_scraper("google", url).fetch_data()

        if not response:
            print(f"[GOOGLE SEARCH] ❌ No response from scraper (returned None)")
            return None

        print(f"[GOOGLE SEARCH] Response status: {response.status_code}")

        if response.status_code != 200:
            error_text = response.text[:500] if response.text else "No error message"
            print(f"[GOOGLE SEARCH] ❌ API Error ({response.status_code}): {error_text}")
            return None

        try:
            data = response.json()
        except Exception as e:
            print(f"[GOOGLE SEARCH] ❌ Failed to parse JSON: {e}")
            print(f"[GOOGLE SEARCH] Response text: {response.text[:500]}")
            return None

        items_count = len(data.get("items", []))
        total_results = int(data.get("searchInformation", {}).get("totalResults", 0))
        print(f"[GOOGLE SEARCH] ✅ Got {items_count} items (total available: {total_results})")

        # Initialize all_items with the first batch of results
        all_items.extend(data.get("items", []))

        # Loop to retrieve additional pages, with a maximum of 5 iterations
        while len(all_items) < total_results:
            loop_count += 1
            if loop_count >= max_loops:
                break

            # Update startIndex based on `nextPage` in each response
            next_page_info = data.get("queries", {}).get("nextPage", [])
            if not next_page_info:
                break  # No more pages available

            # Set the start index for the next page
            start_index = next_page_info[0].get("startIndex", None)
            if start_index is None:
                break  # Safeguard in case `startIndex` is missing

            # Fetch the next page of results
            url = f"{base_url}&start={start_index}&num={max_results_per_page}"
            response = ScraperFactory.get_scraper("google", url).fetch_data()
            data = response.json()

            # Append new items to all_items list
            items = data.get("items", [])
            all_items.extend(items)

            # Stop if no items are returned
            if not items:
                break

        # Place all collected items back into the main response
        data["items"] = all_items
        return data

    @staticmethod
    async def construct_keyword_tracking_query_url(params: GoogleSearchParams) -> str:
        # `includes` - Enforce presence in title and snippet
        includes_query = (
            [
                f'intitle:"{keyword}" OR intext:"{keyword}"'
                for keyword in params.includes
            ]
            if params.includes
            else []
        )

        params.includes = includes_query

        # `or_terms` - Enforce presence in title
        or_terms_query = (
            " ".join([f'intitle:"{term}"' for term in params.or_terms.split()])
            if params.or_terms
            else ""
        )

        params.or_terms = or_terms_query

        # `platforms` - Restrict search to specific sites
        platforms_query = (
            " ".join([f"site:{platform}" for platform in params.platforms])
            if params.platforms
            else ""
        )

        # params.platforms = platforms_query

        url = TextHelper.construct_query_url(params)
        print("Query Url : ", url)
        return url

    @staticmethod
    async def construct_lead_tracking_query_url(params: GoogleSearchParams) -> str:
        queries = []

        # Handle exact phrases (search in title and text)
        if params.phrases:
            formatted_phrases = [f'"{phrase}"' for phrase in params.phrases]
            queries.append(" OR ".join(formatted_phrases))

        # Handle includes (search in title and text)
        if params.includes:
            includes_query = " OR ".join(
                [f'intitle:"{kw}" OR intext:"{kw}"' for kw in params.includes]
            )
            queries.append(includes_query)

        # Handle or_terms (search in title, text, and body)
        if params.or_terms:
            or_terms_query = " OR ".join(
                [f'"{term}"' for term in params.or_terms.split()]
            )
            queries.append(or_terms_query)

        # Handle excludes (exclude from title, text, and body)
        if params.excludes:
            excludes_query = " ".join([f"-{kw}" for kw in params.excludes])
            queries.append(excludes_query)

        # Handle platforms (restrict search to specific sites)
        if params.platforms:
            platforms_query = " OR ".join(
                [f"site:{platform}" for platform in params.platforms]
            )
            queries.append(platforms_query)

        # Combine all query parts into a single query string
        final_query = "&".join(queries).strip()
        # URL-encode the query to ensure it's safe for the request
        encoded_query = quote_plus(final_query)
        return encoded_query

    @staticmethod
    async def extract_dates_from_search_result(search_data: List[dict]):
        """
        Extract dates from search items based on known patterns, including relative and ISO formats.

        Args:
            search_data (List[Dict]): List of search items from the response.

        Returns:
            List[datetime.date]: A list of parsed date objects in consistent date format.
        """
        dates = []

        for item in search_data:
            # Attempt to get date from known `pagemap` metatags fields
            timestamp = item.get("timestamp", "")
            # Process and parse the extracted timestamp
            try:
                date_obj = datetime.fromisoformat(timestamp)
                if date_obj:
                    if date_obj.tzinfo is None:
                        date_obj = date_obj.replace(tzinfo=timezone.utc)
                    dates.append(date_obj)
            except Exception as e:
                print(f"Error parsing timestamp: {e}")
        return dates

    @staticmethod
    async def analyze_comments_sentiment(
        comments: List[dict], text_key: str = "text", concurrency_limit: int = 20
    ) -> dict:
        semaphore = asyncio.Semaphore(concurrency_limit)

        sentiment_summary = {"positive": 0, "negative": 0, "neutral": 0}
        top_positive = {"sentiment": {"score": float("-inf")}}
        top_negative = {"sentiment": {"score": float("-inf")}}

        async def analyze_comment(comment: dict) -> dict:
            text = comment.get(text_key, "")
            if not text:
                comment["sentiment"] = {"sentiment": "neutral", "score": 0}
                return comment

            async with semaphore:
                try:
                    result = await AIService.analyze_sentiment(text)
                    if "sentiment" in result:
                        comment["sentiment"] = result
                    else:
                        raise ValueError("Missing 'sentiment' key in result")
                except Exception as e:
                    print("Exception caught: ", e)
                    comment["sentiment"] = {"sentiment": "neutral", "score": 0}
            return comment

        # Run all comment analysis concurrently
        analyzed_comments = await asyncio.gather(
            *(analyze_comment(comment) for comment in comments)
        )

        # Aggregate sentiment statistics
        for comment in analyzed_comments:
            result = comment["sentiment"]
            sentiment_type = result.get("sentiment", "neutral")
            score = result.get("score", 0)
            sentiment_summary[sentiment_type] += 1

            if (
                sentiment_type == "positive"
                and score > top_positive["sentiment"]["score"]
            ):
                top_positive = comment
            elif (
                sentiment_type == "negative"
                and score > top_negative["sentiment"]["score"]
            ):
                top_negative = comment

        total = sum(sentiment_summary.values())
        sentiment_summary_percent = (
            {k: round((v / total) * 100, 2) for k, v in sentiment_summary.items()}
            if total > 0
            else {"positive": 0, "negative": 0, "neutral": 0}
        )

        return {
            "comments_with_sentiment": analyzed_comments,
            "sentiment_summary": sentiment_summary_percent,
            "top_positive_comment": (
                top_positive
                if top_positive["sentiment"]["score"] != float("-inf")
                else {}
            ),
            "top_negative_comment": (
                top_negative
                if top_negative["sentiment"]["score"] != float("-inf")
                else {}
            ),
        }

    @staticmethod
    async def extract_platforms_from_search_result(search_data: list) -> list:
        """
        Extract platforms from search items based on `displayLink` field.

        Args:
            search_data (List[Dict]): List of search items from the response.

        Returns:
            list: A list of platform names extracted from `displayLink` values.
        """
        platforms = []

        for item in search_data:
            # Extract platform from displayLink
            platform = item.get("platform", "")
            platform_name = await GoogleService.extract_domain(platform)
            if platform_name or platform == "web":
                platforms.append(platform_name or platform)

        return platforms

    @staticmethod
    async def extract_domain(url: str) -> str:
        """
        Parse the main domain from a URL (e.g., 'za.linkedin.com' becomes 'linkedin').

        Args:
            url (str): URL string to extract the domain.

        Returns:
            str: Extracted platform name if valid, otherwise an empty string.
        """
        try:
            # Extract the domain without subdomains and TLD
            domain_parts = urlparse(f"https://{url}").netloc.split(".")
            if len(domain_parts) > 1:
                return domain_parts[-2]  # Get second-to-last part as the main domain
        except Exception as e:
            print(f"Error extracting domain: {e}")
        return ""

    @staticmethod
    async def analyze_entities(text: str) -> list:
        """
        Perform entity analysis on a given text using Google Cloud Natural Language API to support word cloud generation.

        Args:
            text (str): Text to analyze for entities.

        Returns:
            list: A list of dictionaries with words and their frequency.
        """
        client = GoogleService.get_nlp_client()
        document = language_v1.Document(
            content=text, type_=language_v1.Document.Type.PLAIN_TEXT
        )

        try:
            response = client.analyze_entities(document=document)
        except Exception as e:
            return [{"error": str(e)}]

        # Count occurrences of each entity for the word cloud
        entity_counts: dict = {}
        for entity in response.entities:
            entity_text = entity.name.lower()

            # Only include single words, excluding phrases and sentences
            if " " not in entity_text:
                entity_counts[entity_text] = entity_counts.get(entity_text, 0) + 1

        print("Entity Count : ", entity_counts)
        return [{"word": word, "count": count} for word, count in entity_counts.items()]

    @staticmethod
    async def get_word_cloud_data(texts: list) -> list:
        """
        Generate word cloud data from a list of texts using entity analysis.

        Args:
            texts (list): List of text snippets to analyze.

        Returns:
            list: A list of dictionaries representing words and their total counts across all texts.
        """
        aggregate_entity_counts: dict = {}

        # Iterate through each text, performing entity analysis and aggregating counts
        for text in texts:
            entity_data = await GoogleService.analyze_entities(text)
            for entry in entity_data:
                # Check if 'word' and 'count' are in the entry to avoid KeyError
                if "word" in entry and "count" in entry:
                    word = entry["word"]
                    count = entry["count"]
                    aggregate_entity_counts[word] = (
                        aggregate_entity_counts.get(word, 0) + count
                    )

        # Format aggregated counts for word cloud
        word_cloud_data = [
            {"word": word, "count": count}
            for word, count in aggregate_entity_counts.items()
        ]
        return word_cloud_data

    @staticmethod
    def get_nlp_client():
        """
        Initialize and return the Google NLP client using service account credentials.

        Returns:
            language_v1.LanguageServiceClient: An authenticated NLP client.
        """
        credentials_path = settings.GOOGLE_APPLICATION_CREDENTIALS
        if os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            client = language_v1.LanguageServiceClient(credentials=credentials)
        else:
            raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

        return client
