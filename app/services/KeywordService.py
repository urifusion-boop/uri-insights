from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json
import re
from app.core.helpers.keyword_helper import KeywordHelper
from app.services.GoogleService import GoogleService
from typing import Any, List, Optional
from app.domain.requests.google_requests import GoogleSearchParams
from app.domain.responses.uri_response import UriResponse
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.core.helpers.date_helper import DateHelper
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.helpers.text_helper import TextHelper
from app.core.processors.location_processor import LocationProcessor
from app.services.AIService import AIService
from app.domain.models.chat_model import (
    ChatModel,
    KeywordConversationInsight,
    TweetOptimizationResponse,
)
from app.domain.enums.ai_prompt import AIChiefAnalystPrompt


class KeywordService:
    CACHE_TTL = timedelta(hours=2000)  # Set cache expiration time (e.g., 1 hour)

    @staticmethod
    async def fetch_keyword_insight(params: GoogleSearchParams) -> Any:
        response = await GoogleService.get_search_data(params)
        if response.status_code == 200:
            data = response.json()
            return UriResponse.get_single_data_response("keyword results", data)
        else:
            return UriResponse.get_single_data_response("keyword results", None)

    @staticmethod
    async def fetch_batch_keyword_insight(
        db: AsyncIOMotorDatabase, params: GoogleSearchParams
    ) -> Any:
        response_name = "keyword results"
        cache_key = CacheHelper.generate_cache_key(TextHelper.to_string(params))
        cached_data = await KeywordService.get_cached_data(db, cache_key)

        if cached_data:
            print("Returning cached data")
            return UriResponse.get_single_data_response(
                response_name, {"cache_key": cache_key, **cached_data}
            )

        await CacheRepository.clear_cache_by_contains(db, cache_key)

        search_data = await GoogleService.get_multiple_search_data(params=params)
        if not search_data:
            raise ValueError("Search data not found")
        response = KeywordHelper.unify_tracker_data(search_data)
        response_posts = response.get("posts", [])
        response_influencers = response.get("influencers")
        response_influencer_ratings = await KeywordService.__process_influencers_rating(
            response_influencers
        )
        response.get("metadata", {}).update(response_influencer_ratings)
        if not response_posts:
            return UriResponse.get_single_data_response(response_name, None)

        await CacheRepository.set_cache(db, cache_key, response, ttl=timedelta(hours=8))
        return UriResponse.get_single_data_response(
            response_name, {"cache_key": cache_key, **response}
        )

    @staticmethod
    async def get_web_keyword_sentiment(
        db: AsyncIOMotorDatabase, params: GoogleSearchParams
    ) -> Any:
        cache_key = "keyword-web-sentiment-data-" + CacheHelper.generate_cache_key(
            TextHelper.to_string(params)
        )

        data = await KeywordService.get_cached_data(db, cache_key)

        if not data:
            # Extract full response data
            extracted_data = await KeywordService.extract_batch_keyword_data(db, params)
            # Prepare comments for sentiment analysis
            # comments = [{"comment": item["comment"]} for item in extracted_data]

            # Analyze sentiment only on comments
            sentiment_analysis = await GoogleService.analyze_comments_sentiment(
                extracted_data, "comment"
            )

            # Update each item in extracted data with its corresponding sentiment
            for i, item in enumerate(extracted_data):
                item["sentiment"] = sentiment_analysis["comments_with_sentiment"][i][
                    "sentiment"
                ]

            # Cache the final sentiment analysis result
            result = {
                "total_results": len(extracted_data),
                "sentiment": extracted_data,
                "overall_sentiment": sentiment_analysis["sentiment_summary"],
                "top_positive_comment": sentiment_analysis["top_positive_comment"],
                "top_negative_comment": sentiment_analysis["top_negative_comment"],
            }

            await CacheRepository.set_cache(
                db, cache_key, result, ttl=timedelta(hours=8)
            )
            return UriResponse.get_single_data_response(
                "keyword sentiment", {**result, "web_sentiment_cache_key": cache_key}
            )
        else:
            extracted_data = data

        return UriResponse.get_single_data_response("keyword sentiment", extracted_data)

    @staticmethod
    async def extract_batch_keyword_data(
        db: AsyncIOMotorDatabase, params: GoogleSearchParams
    ) -> Any:
        posts = await KeywordService.get_batch_keyword_posts(db, params)
        extracted_data = []

        cache_key = "extracted-keyword-items-" + CacheHelper.generate_cache_key(
            TextHelper.to_string(params)
        )
        cached_data = await KeywordService.get_cached_data(db, cache_key)

        if cached_data:
            return cached_data

        for post in posts:
            # Extract author information from various fields, fallback to website domain if unavailable
            author = post.get("author", {})

            # Determine the comment/description content
            snippet = post.get("text", "")
            title = post.get("title", "")
            description = post.get("snippet", {})

            # Check if snippet is meaningful; otherwise, use title or description
            if snippet.lower().startswith("posted by"):
                comment = title  # Use title if snippet is just "posted by" text
            elif snippet:
                comment = snippet  # Use snippet if it contains meaningful text
            else:
                comment = (
                    description or title
                )  # Fallback to description or title if snippet is empty

            # Extract timestamp from various possible fields
            timestamp = post.get("timestamp")

            # Extract image URL from various possible fields
            image_list = post.get("pagemap", {}).get("cse_image", [])

            image = image_list[0].get("src") if image_list else None

            # Extract the website domain or source
            website = post.get("link")

            # Append structured data for this item
            extracted_data.append(
                {
                    "author": author,
                    "comment": comment,
                    "timestamp": timestamp,
                    "image": image,
                    "website": website,
                }
            )

        if len(extracted_data) > 0:
            await CacheRepository.set_cache(
                db, cache_key, extracted_data, ttl=timedelta(hours=8)
            )
        return extracted_data

    # @staticmethod
    # def extract_batch_keyword_data_no_cache(
    #     items: list,
    #     db: AsyncIOMotorDatabase,
    #     user_id: str,
    #     keywords: List[str],
    #     business_summary: str,
    # ) -> Any:
    #     extracted_data = []
    #     leads_to_insert = []
    #     for item in items:
    #         lead = LeadService.generate_single_lead_insight(business_summary, item)

    #         if lead and lead is not None:
    #             existing_lead = db["leads"].find_one(
    #                 {
    #                     "assigned_to": user_id,
    #                     "mention": lead.get("mention"),
    #                     "social_profile": lead.get("social_profile"),
    #                 }
    #             )
    #             if not existing_lead:
    #                 leads_to_insert.append(
    #                     LeadCreate(
    #                         first_name=lead.get("first_name"),
    #                         last_name=lead.get("last_name"),
    #                         keywords=keywords,
    #                         username=lead.get("username"),
    #                         email=lead.get("email"),
    #                         phone=lead.get("phone"),
    #                         location=lead.get("location"),
    #                         notes=lead.get("notes"),
    #                         tags=lead.get("tags"),
    #                         score=lead.get("score"),
    #                         social_profile=lead.get("social_profile"),
    #                         social_profile_link=lead.get("social_profile_link"),
    #                         company_name=lead.get("company_name"),
    #                         job_title=lead.get("job_title"),
    #                         industry=lead.get("industry"),
    #                         mention=lead.get("mention"),
    #                         summary_of_mention=lead.get("summary_of_mention"),
    #                         interest_level=lead.get("interest_level"),
    #                         opportunity_type=lead.get("opportunity_type"),
    #                         lead_reason=lead.get("lead_reason"),
    #                         follow_up_message=lead.get("follow_up_message"),
    #                         follow_up_approach=lead.get("follow_up_approach"),
    #                         lead_source=lead.get("lead_source"),
    #                         lead_status="New",
    #                         assigned_to=user_id,
    #                     )
    #                 )

    #             # Step 7: Bulk insert leads
    #             if leads_to_insert:
    #                 LeadRepository.multiple_create_leads(db, leads_to_insert)

    #             # Can create helper method to extract the notification data from the inserted leads
    #             # Send summary of Lead Notification here: NotificationService.notifyNewLeads(#put the data here)

    #         # Extract author information from various fields, fallback to website domain if unavailable
    #         author = (
    #             item.get("pagemap", {}).get("hcard", [{}])[0].get("fn")
    #             or item.get("pagemap", {}).get("metatags", [{}])[0].get("author")
    #             or item.get("displayLink")
    #         )

    #         # Determine the comment/description content
    #         snippet = item.get("snippet", "")
    #         title = item.get("title", "")
    #         description = (
    #             item.get("pagemap", {}).get("metatags", [{}])[0].get("og:description")
    #             or ""
    #         )

    #         # Check if snippet is meaningful; otherwise, use title or description
    #         if snippet.lower().startswith("posted by"):
    #             comment = title  # Use title if snippet is just "posted by" text
    #         elif snippet:
    #             comment = snippet  # Use snippet if it contains meaningful text
    #         else:
    #             comment = (
    #                 description or snippet or title
    #             )  # Fallback to description or title if snippet is empty

    #         # Extract timestamp from various possible fields
    #         timestamp = GoogleService.get_timestamp_from_search(item)

    #         # Extract image URL from various possible fields
    #         image = item.get("pagemap", {}).get("cse_image", [{}])[0].get(
    #             "src"
    #         ) or item.get("pagemap", {}).get("metatags", [{}])[0].get("og:image")

    #         # Extract the website domain or source
    #         website = item.get("displayLink", "")

    #         # Append structured data for this item
    #         extracted_data.append(
    #             {
    #                 "author": author,
    #                 "comment": comment,
    #                 "timestamp": timestamp,
    #                 "image": image,
    #                 "website": website,
    #             }
    #         )

    #     return extracted_data

    @staticmethod
    async def get_keyword_daily_frequency_data(
        db: AsyncIOMotorDatabase, cache_key: str
    ):
        """
        Calculate the frequency of dates and format it for JSON output.

        Returns:
            list: List of dictionaries with date counts, sorted by date.
        """
        search_data = (await KeywordService.get_cached_data(db, cache_key)).get(
            "posts", []
        )
        dates = await GoogleService.extract_dates_from_search_result(search_data)
        date_counts = Counter(dates)

        # Format each date and count, ensure dates are in YYYY-MM-DD format
        daily_data = [
            {"date": date.strftime("%Y-%m-%d"), "count": count}
            for date, count in sorted(date_counts.items())
        ]
        return UriResponse.get_list_data_response("daily mention", daily_data)

    @staticmethod
    async def get_platform_frequency_data(
        db: AsyncIOMotorDatabase, cache_key: str
    ) -> list:
        """
        Calculate the frequency of platforms from displayLink and return in JSON-compatible format.

        Args:
            search_data (List[Dict]): List of search items from the response.

        Returns:
            list: List of dictionaries with platform names and their counts.
        """

        search_data = (await KeywordService.get_cached_data(db, cache_key)).get(
            "posts", []
        )
        platforms = await GoogleService.extract_platforms_from_search_result(
            search_data
        )
        platform_counts = Counter(platforms)

        # Format for JSON output, sorted alphabetically by platform name
        platform_data = [
            {"platform": platform, "count": count}
            for platform, count in sorted(platform_counts.items())
        ]
        return UriResponse.get_list_data_response("platform", platform_data)

    @staticmethod
    async def get_post_type_frequency(
        db: AsyncIOMotorDatabase, cache_key: str
    ) -> List[dict]:
        """
        Calculates the frequency of different post types based on link, displayLink, and snippet patterns.

        Args:
            search_data (List[Dict]): The search result items from the API.

        Returns:
            List[Dict]: A list of dictionaries with each post type and its corresponding frequency.
        """

        search_data = (await KeywordService.get_cached_data(db, cache_key)).get(
            "posts", []
        )
        post_types = []

        if search_data:

            for post in search_data:
                post_platform = post.get("platform")
                post_link = post.get("link")
                post_title = post.get("title")
                post_snippet = post.get("text")
                # Categorize known social media platforms as "social_media"
                social_media_domains = [
                    "facebook.com",
                    "twitter.com",
                    "instagram.com",
                    "tiktok.com",
                    "linkedin.com",
                    "threads.net",
                    "x.com",
                    "snapchat.com",
                    "pinterest.com",
                ]
                if any(platform == post_platform for platform in social_media_domains):
                    post_types.append("social_media")
                elif "youtube.com" in post_link or "vimeo.com" in post_link:
                    post_types.append("video")
                elif (
                    "blog" in post_title
                    or "article" in post_title
                    or "guide" in post_title
                ):
                    post_types.append("blog_article")
                elif "product" in post_snippet:
                    post_types.append("product")
                elif post_platform == "reddit.com":
                    post_types.append("forum_post")
                else:
                    post_types.append("general_web")

            # Count occurrences of each post type
            post_type_counts = Counter(post_types)

            # Format results for output
            post_type_data = [
                {"post_type": post_type, "count": count}
                for post_type, count in post_type_counts.items()
            ]
            return UriResponse.get_list_data_response("Post type", post_type_data)
        return UriResponse.get_list_data_response("Post type", [])

    @staticmethod
    async def get_country_code_frequency(
        db: AsyncIOMotorDatabase, cache_key: str
    ) -> List[dict]:
        """
        Calculates the frequency of country codes based on displayLink patterns.

        Args:
            search_data (List[Dict]): The search result items from the API.

        Returns:
            List[Dict]: A list of dictionaries with each country code and its corresponding frequency.
        """

        search_data = (await KeywordService.get_cached_data(db, cache_key)).get(
            "posts", []
        )
        country_codes = []

        for post in search_data:
            # Check displayLink or link for country code
            post_link = post.get("link")

            # Extract country code using regex on subdomain (e.g., "za.linkedin.com" -> "za")
            match = re.match(r"\b(?:https?://)?(?:www\.)?[\w-]+\.(\w{2})\b", post_link)
            if match:
                country_code = match.group(1).lower()
                if TextHelper.is_valid_country_code(country_code):
                    country_codes.append(country_code)

        # Count occurrences of each country code
        country_code_counts = Counter(country_codes)

        # Format results for output
        country_code_data = [
            {"country_code": code, "count": count}
            for code, count in country_code_counts.items()
        ]

        return UriResponse.get_list_data_response("Country code", country_code_data)

    @staticmethod
    async def get_word_cloud_data(db: AsyncIOMotorDatabase, cache_key: str) -> list:
        top_words_cache_key = "top-words-" + cache_key
        cached_data = await KeywordService.get_cached_data(db, top_words_cache_key)
        if cached_data:
            return UriResponse.get_list_data_response("top word", cached_data)
        search_data = (await KeywordService.get_cached_data(db, cache_key)).get(
            "posts", []
        )
        titles = [item["title"] for item in search_data if "title" in item]
        data = await GoogleService.get_word_cloud_data(titles)
        if data and len(data) > 0:
            await CacheRepository.set_cache(
                db, top_words_cache_key, data, ttl=timedelta(hours=8)
            )
        return UriResponse.get_list_data_response("top word", data)

    @staticmethod
    async def get_cached_data(db: AsyncIOMotorDatabase, cache_key: Any) -> Any:

        # Check if cached data exists and is valid
        return await CacheRepository.get_cache(db, cache_key) or {}

    @staticmethod
    async def get_batch_keyword_posts(
        db: AsyncIOMotorDatabase, params: GoogleSearchParams
    ) -> Any:
        try:
            data = await KeywordService.fetch_batch_keyword_insight(db, params)
            if not data or "responseData" not in data:
                return []

            posts = data["responseData"].get("posts", [])
            return posts
        except ValueError as e:
            print("Value Error occurred: ", e)
        except Exception as e:
            print("Exception occurred: ", e)

    @staticmethod
    async def get_geographical_heatmap_data(twitter_data: dict) -> dict:
        """
        Generate geographical heatmap data from Twitter recent search service response.

        Args:
            twitter_data (dict): The Twitter recent search API response data.

        Returns:
            dict: Heatmap data containing location counts.
        """
        heatmap_data = []
        users = twitter_data.get("includes", {}).get("users", [])

        # Extract location data from user profiles
        for user in users:
            location = user.get("location")
            if location:
                heatmap_data.append(location)

        # Count occurrences of each location
        location_counts = Counter(heatmap_data)

        # Format data for JSON output
        formatted_data = [
            {"location": location, "count": count}
            for location, count in location_counts.items()
        ]

        # Sort by count in descending order for better visualization
        formatted_data.sort(key=lambda x: x["count"], reverse=True)
        return UriResponse.get_list_data_response(
            "geographical heatmap data", formatted_data
        )

    @staticmethod
    async def get_hashtag_data(twitter_data: dict) -> dict[str, Any]:
        """
        Generate hashtag data from the Twitter data.
        """
        hashtag_counter: Counter = Counter()
        tweets = twitter_data.get("responseData", {}).get("data", [])

        for tweet in tweets:
            hashtags = tweet.get("entities", {}).get("hashtags", [])
            for hashtag in hashtags:
                hashtag_counter[hashtag["tag"].lower()] += 1

        hashtag_data = [
            {"hashtag": hashtag, "count": count}
            for hashtag, count in hashtag_counter.items()
        ]
        hashtag_data.sort(key=lambda x: x["count"], reverse=True)

        return UriResponse.get_list_data_response("top hashtag", hashtag_data)

    @staticmethod
    async def get_x_top_mentioned_countries(db, cache_key: str) -> Any:
        """
        Generate heatmap data from Twitter API response, including location frequency.

        Args:
            db: AsyncIOMotorDatabase connection
            cache_key: Cache key to fetch stored Twitter response data

        Returns:
            Dict: Heatmap data grouped by user location with aggregated metrics and location frequency.
        """
        twitter_response = await KeywordService.get_cached_data(db, cache_key)

        # Aggregated data
        location_metrics: dict = defaultdict(
            lambda: {
                "tweet_count": 0,
                "retweet_count": 0,
                "reply_count": 0,
                "like_count": 0,
                "quote_count": 0,
                "impression_count": 0,
                "location_frequency": 0,  # Counts how many times this location appears
            }
        )
        country_metrics: dict = defaultdict(
            lambda: {
                "tweet_count": 0,
                "retweet_count": 0,
                "reply_count": 0,
                "like_count": 0,
                "quote_count": 0,
                "impression_count": 0,
                "location_frequency": 0,  # Counts how many times this country appears
            }
        )

        # Extract users and map their IDs to normalized locations
        user_locations: dict = {
            user["id"]: (LocationProcessor.normalize_location(user.get("location", "")))
            for user in twitter_response.get("includes", {}).get("users", [])
            if "location" in user
        }

        # Process tweets and group by location
        for tweet in twitter_response.get("data", []):
            author_id = tweet.get("author_id")
            raw_location = user_locations.get(author_id)

            if not raw_location:
                continue

            normalized_location = LocationProcessor.normalize_location(raw_location)
            country_name = LocationProcessor.extract_country(normalized_location)

            # Aggregate metrics by location
            metrics = tweet.get("public_metrics", {})
            location_metrics[normalized_location]["tweet_count"] += 1
            location_metrics[normalized_location]["retweet_count"] += metrics.get(
                "retweet_count", 0
            )
            location_metrics[normalized_location]["reply_count"] += metrics.get(
                "reply_count", 0
            )
            location_metrics[normalized_location]["like_count"] += metrics.get(
                "like_count", 0
            )
            location_metrics[normalized_location]["quote_count"] += metrics.get(
                "quote_count", 0
            )
            location_metrics[normalized_location]["impression_count"] += metrics.get(
                "impression_count", 0
            )
            location_metrics[normalized_location]["location_frequency"] += 1

            # Aggregate metrics by country
            country_metrics[country_name]["tweet_count"] += 1
            country_metrics[country_name]["retweet_count"] += metrics.get(
                "retweet_count", 0
            )
            country_metrics[country_name]["reply_count"] += metrics.get(
                "reply_count", 0
            )
            country_metrics[country_name]["like_count"] += metrics.get("like_count", 0)
            country_metrics[country_name]["quote_count"] += metrics.get(
                "quote_count", 0
            )
            country_metrics[country_name]["impression_count"] += metrics.get(
                "impression_count", 0
            )
            country_metrics[country_name]["location_frequency"] += 1

        # Convert to sorted lists
        top_locations = sorted(
            [{"location": loc, **metrics} for loc, metrics in location_metrics.items()],
            key=lambda x: x["tweet_count"],
            reverse=True,
        )
        top_countries = sorted(
            [
                {"country": country, **metrics}
                for country, metrics in country_metrics.items()
            ],
            key=lambda x: x["tweet_count"],
            reverse=True,
        )

        return UriResponse.get_single_data_response(
            "top locations and countries",
            {"top_locations": top_locations, "top_countries": top_countries},
        )

    @staticmethod
    async def process_mentions(db: AsyncIOMotorDatabase, cache_key: str) -> Any:
        data = await KeywordService.get_cached_data(db, cache_key)
        tweets = data.get("data", [])
        includes_users = data.get("includes", {}).get("users", [])

        # Placeholder for user details
        user_followers = {
            user["id"]: user.get("public_metrics", {}).get("followers_count", 0)
            for user in includes_users
        }
        users_set = set(user_followers.keys())

        # Aggregated Metrics
        total_mentions = len(tweets)
        total_users = len(users_set)
        total_engagements = 0
        total_reach = 0
        total_comments = 0
        total_impressions = 0

        # Chart Data Structure
        mentions_data: dict = defaultdict(
            lambda: {
                "time": None,
                "comment": "",
                "retweets": 0,
                "replies": 0,
                "likes": 0,
                "quotes": 0,
                "impressions": 0,
                "hashtags": [],
                "mentions": [],
            }
        )

        for tweet in tweets:
            created_at = tweet.get("created_at")
            if not created_at:
                continue

            tweet_id = tweet.get("id")
            public_metrics = tweet.get("public_metrics", {})
            author_id = tweet.get("author_id")
            hashtags = [
                tag.get("tag") for tag in tweet.get("entities", {}).get("hashtags", [])
            ]
            mentions = [
                mention.get("username")
                for mention in tweet.get("entities", {}).get("mentions", [])
            ]

            # Aggregation
            total_engagements += public_metrics.get(
                "retweet_count", 0
            ) + public_metrics.get("like_count", 0)
            total_comments += public_metrics.get("reply_count", 0)
            total_impressions += public_metrics.get("impression_count", 0)
            total_reach += public_metrics.get(
                "impression_count", 0
            )  # Add impressions directly
            total_reach += user_followers.get(
                author_id, 0
            )  # Add author's follower count

            # Build Chart Data
            date_key = datetime.strptime(
                created_at, "%Y-%m-%dT%H:%M:%S.%fZ"
            ).isoformat()
            mentions_data[date_key]["time"] = date_key
            mentions_data[date_key]["retweets"] += public_metrics.get(
                "retweet_count", 0
            )
            mentions_data[date_key]["replies"] += public_metrics.get("reply_count", 0)
            mentions_data[date_key]["likes"] += public_metrics.get("like_count", 0)
            mentions_data[date_key]["quotes"] += public_metrics.get("quote_count", 0)
            mentions_data[date_key]["impressions"] += public_metrics.get(
                "impression_count", 0
            )
            mentions_data[date_key]["comment"] = tweet.get("text", "")
            mentions_data[date_key]["hashtags"].extend(hashtags)
            mentions_data[date_key]["mentions"].extend(mentions)

        # Convert to list and sort by time
        chart_data = list(mentions_data.values())
        chart_data.sort(key=lambda x: x["time"])

        # Format Response
        mentions_data = {
            "mentions_count": total_mentions,
            "users_count": total_users,
            "engagements_count": total_engagements,
            "reach_count": total_reach,
            "comments_count": total_comments,
            "impressions_count": total_impressions,
            "chart_data": chart_data,
        }

        return UriResponse.get_single_data_response("mentions", mentions_data)

    @staticmethod
    async def fetch_twitter_posts(db: AsyncIOMotorDatabase, cache_key: str) -> Any:
        data = await KeywordService.get_cached_data(db, cache_key)

        tweets = data.get("data", [])
        includes_users = data.get("includes", {}).get("users", [])

        # Placeholder for user details
        user_details = {
            user["id"]: {
                "username": user.get("username"),
                "profile_image_url": user.get("profile_image_url"),
                "followers_count": user.get("public_metrics", {}).get(
                    "followers_count", 0
                ),
            }
            for user in includes_users
        }

        # Aggregated Metrics
        total_posts = len(tweets)
        total_users = len(user_details)
        total_engagements = 0

        # Post Data Structure
        posts_data = []

        for tweet in tweets:
            created_at = tweet.get("created_at")
            if not created_at:
                continue

            tweet_id = tweet.get("id")
            public_metrics = tweet.get("public_metrics", {})
            author_id = tweet.get("author_id")
            entities = tweet.get("entities", {})
            media = tweet.get("attachments", {}).get("media_keys", [])
            hashtags = [tag.get("tag") for tag in entities.get("hashtags", [])]
            mentions = [
                mention.get("username") for mention in entities.get("mentions", [])
            ]

            # Post Details
            post_details = {
                "time": datetime.strptime(
                    created_at, "%Y-%m-%dT%H:%M:%S.%fZ"
                ).isoformat(),
                "text": tweet.get("text", ""),
                "retweets": public_metrics.get("retweet_count", 0),
                "replies": public_metrics.get("reply_count", 0),
                "likes": public_metrics.get("like_count", 0),
                "quotes": public_metrics.get("quote_count", 0),
                "impressions": public_metrics.get("impression_count", 0),
                "hashtags": hashtags,
                "mentions": mentions,
                "media": media,  # Media keys can be used to fetch media URLs from includes
                "username": user_details.get(author_id, {}).get("username"),
                "profile_image_url": user_details.get(author_id, {}).get(
                    "profile_image_url"
                ),
                "followers_count": user_details.get(author_id, {}).get(
                    "followers_count"
                ),
            }

            total_engagements += (
                public_metrics.get("retweet_count", 0)
                + public_metrics.get("reply_count", 0)
                + public_metrics.get("like_count", 0)
            )

            posts_data.append(post_details)

        # Format Response
        posts_response = {
            "posts_count": total_posts,
            "users_count": total_users,
            "engagements_count": total_engagements,
            "posts_data": posts_data,
        }

        return UriResponse.get_single_data_response("post", posts_response)

    @staticmethod
    async def process_twitter_posts(db: AsyncIOMotorDatabase, cache_key: str) -> Any:
        processed_posts_cache_key = "processed-twitter-posts-" + cache_key
        processed_posts_cache_data = await KeywordService.get_cached_data(
            db, processed_posts_cache_key
        )

        if processed_posts_cache_data:
            return UriResponse.get_single_data_response(
                "post", processed_posts_cache_data
            )

        data = await KeywordService.get_cached_data(db, cache_key)

        tweets = data.get("data", [])
        includes_users = data.get("includes", {}).get("users", [])
        includes_media = data.get("includes", {}).get("media", [])

        # Placeholder for user details
        user_details = {
            user["id"]: {
                "username": user.get("username"),
                "profile_image_url": user.get("profile_image_url"),
                "followers_count": user.get("public_metrics", {}).get(
                    "followers_count", 0
                ),
            }
            for user in includes_users
        }

        # Map media keys to media URLs
        media_details = {
            media["media_key"]: media.get("url", media.get("preview_image_url"))
            for media in includes_media
        }

        # Aggregated Metrics
        total_posts = len(tweets)
        total_users = len(user_details)
        total_engagements = 0

        # Post Data Structure
        posts_data = []
        post_types: Counter = Counter()
        hashtag_counter: Counter = Counter()
        mention_counter: Counter = Counter()

        for tweet in tweets:
            created_at = tweet.get("created_at")
            if not created_at:
                continue

            tweet_id = tweet.get("id")
            public_metrics = tweet.get("public_metrics", {})
            author_id = tweet.get("author_id")
            entities = tweet.get("entities", {})
            media_keys = tweet.get("attachments", {}).get("media_keys", [])
            hashtags = [
                tag.get("tag").lower() for tag in entities.get("hashtags", [])
            ]  # Convert to lowercase for uniformity
            mentions = [
                mention.get("username").lower()
                for mention in entities.get("mentions", [])
            ]  # Convert to lowercase for uniformity

            # Increment hashtag and mention frequency
            hashtag_counter.update(hashtags)
            mention_counter.update(mentions)

            # Determine Post Type
            if "referenced_tweets" in tweet:
                for ref in tweet["referenced_tweets"]:
                    post_types[ref["type"]] += 1
            else:
                post_types[
                    "original"
                ] += 1  # Default to original if no referenced tweets

            # Get media URLs for the tweet
            media_urls = [media_details.get(media_key) for media_key in media_keys]

            # Post Details
            post_details = {
                "id": tweet_id,
                "time": datetime.strptime(
                    created_at, "%Y-%m-%dT%H:%M:%S.%fZ"
                ).isoformat(),
                "text": tweet.get("text", ""),
                "retweets": public_metrics.get("retweet_count", 0),
                "replies": public_metrics.get("reply_count", 0),
                "likes": public_metrics.get("like_count", 0),
                "quotes": public_metrics.get("quote_count", 0),
                "impressions": public_metrics.get("impression_count", 0),
                "hashtags": hashtags,
                "mentions": mentions,
                "media_urls": [
                    url for url in media_urls if url
                ],  # Only include valid URLs
                "username": user_details.get(author_id, {}).get("username"),
                "profile_image_url": user_details.get(author_id, {}).get(
                    "profile_image_url"
                ),
                "followers_count": user_details.get(author_id, {}).get(
                    "followers_count"
                ),
            }

            total_engagements += (
                public_metrics.get("retweet_count", 0)
                + public_metrics.get("reply_count", 0)
                + public_metrics.get("like_count", 0)
            )

            posts_data.append(post_details)

        # Calculate Percentages for Post Types
        post_type_counts = dict(post_types)
        post_type_percentages = {
            post_type: (count / total_posts) * 100 if total_posts > 0 else 0
            for post_type, count in post_type_counts.items()
        }

        # Get Top Hashtags and Mentions
        top_hashtags = hashtag_counter.most_common(
            10
        )  # Adjust the number for more or fewer top hashtags
        top_mentions = mention_counter.most_common(
            10
        )  # Adjust the number for more or fewer top mentions

        # Format Response
        posts_response = {
            "posts_count": total_posts,
            "users_count": total_users,
            "engagements_count": total_engagements,
            "post_types": {
                "counts": post_type_counts,
                "percentages": post_type_percentages,
            },
            "top_hashtags": [
                {"tag": tag, "count": count} for tag, count in top_hashtags
            ],
            "top_mentions": [
                {"username": mention, "count": count} for mention, count in top_mentions
            ],
            "posts_data": posts_data,
        }

        if posts_data and len(posts_data) > 0:
            await CacheRepository.set_cache(
                db, processed_posts_cache_key, posts_response, ttl=timedelta(hours=24)
            )
        return UriResponse.get_single_data_response("post", posts_response)

    @staticmethod
    async def calculate_engagement(influencer: dict) -> int:
        """
        Calculate engagement as the sum of retweets, replies, likes, and quotes.
        """
        return sum(
            influencer.get(metric, 0)
            for metric in ["retweet_count", "reply_count", "like_count", "quote_count"]
        )

    @staticmethod
    async def process_influencers(db: AsyncIOMotorDatabase, cache_key: str) -> dict:
        data = await KeywordService.get_cached_data(db, cache_key)
        influencer_details = []
        demographics: dict = defaultdict(lambda: {"count": 0, "percentage": 0.0})
        engagement_data = []

        # Extract tweets and user details
        tweets = data.get("data", [])
        includes_users = data.get("includes", {}).get("users", [])

        # Map users by their ID for easy lookup
        users_by_id = {user["id"]: user for user in includes_users}

        # Identify authors from tweets
        author_ids = {tweet["author_id"] for tweet in tweets if "author_id" in tweet}

        # Process only authors
        for author_id in author_ids:
            user = users_by_id.get(author_id)
            if not user:
                continue

            user_data = {
                "id": user.get("id"),
                "name": user.get("name"),
                "username": user.get("username"),
                "date_joined": user.get("created_at"),
                "profile_image_url": user.get("profile_image_url"),
                "bio": user.get("description"),
                "location": LocationProcessor.normalize_location(
                    user.get("location", "")
                ),
                "country": LocationProcessor.extract_country(user.get("location", "")),
                "verified": bool(user.get("verified", "")),
                "gender": user.get(
                    "gender", "Unknown"
                ),  # Assume gender field if present
                "metrics": user.get("public_metrics", {}),
            }

            # Calculate engagement score
            user_data["engagement_score"] = await KeywordService.calculate_engagement(
                user_data["metrics"]
            )

            influencer_details.append(user_data)
            engagement_data.append(user_data)

            # Demographic aggregation
            demographics["verified" if user_data["verified"] else "unverified"][
                "count"
            ] += 1
            demographics[user_data["gender"]]["count"] += 1

        # Calculate percentages
        total_influencers = len(influencer_details)
        for key in demographics:
            demographics[key]["percentage"] = (
                (demographics[key]["count"] / total_influencers) * 100
                if total_influencers > 0
                else 0.0
            )

        # Sort engagement data for top 5 most and least engaging
        engagement_data = sorted(
            engagement_data, key=lambda x: x["engagement_score"], reverse=True
        )
        top_5_most_engaging = engagement_data[:5]
        top_5_least_engaging = (
            engagement_data[-5:] if len(engagement_data) >= 5 else engagement_data
        )

        # Prepare the final data structure
        data = {
            "influencers": influencer_details,
            "demographics": demographics,
            "total_influencers": total_influencers,
            "total_verified": demographics["verified"]["count"],
            "total_unverified": demographics["unverified"]["count"],
            "total_males": demographics["Male"]["count"],
            "total_females": demographics["Female"]["count"],
            "top_5_most_engaging": top_5_most_engaging,
            "top_5_least_engaging": top_5_least_engaging,
        }
        return UriResponse.get_list_data_response("influencer", data)

    @staticmethod
    async def process_twitter_sentiments(
        db: AsyncIOMotorDatabase, twitter_cache_key: str
    ) -> Any:
        # Check if the processed Twitter sentiments data is already cached
        processed_x_sentiments_cache_data = await KeywordService.get_cached_data(
            db, "processed-twitter-sentiments-" + twitter_cache_key
        )
        if processed_x_sentiments_cache_data:
            return UriResponse.get_single_data_response(
                "twitter sentiment", processed_x_sentiments_cache_data
            )

        # Check if processed Twitter posts data exists
        processed_posts_cache_data = await KeywordService.get_cached_data(
            db, "processed-twitter-posts-" + twitter_cache_key
        )
        if not processed_posts_cache_data:
            return UriResponse.get_single_data_response("twitter sentiment", None)

        # Extract posts for sentiment analysis
        posts = processed_posts_cache_data.get("posts_data", [])
        # comments = [{"comment": post.get("text", "")} for post in posts]

        # Analyze sentiments
        sentiment_analysis = await GoogleService.analyze_comments_sentiment(posts)

        # Update each post with its sentiment data
        for i, post in enumerate(posts):
            post["sentiment"] = sentiment_analysis["comments_with_sentiment"][i][
                "sentiment"
            ]
            post["author"] = post.pop("username", None)
            post["comment"] = post.pop("text", None)
            post["timestamp"] = post.pop("time", None)
            post["image"] = post.pop("profile_image_url", None)
            post["website"] = "twitter.com"

        # Prepare the result with required structure
        result = {
            "total_results": len(posts),
            "sentiment": posts,
            "overall_sentiment": sentiment_analysis["sentiment_summary"],
            "top_positive_comment": sentiment_analysis["top_positive_comment"],
            "top_negative_comment": sentiment_analysis["top_negative_comment"],
        }

        # Cache the final sentiment analysis result
        await CacheRepository.set_cache(
            db,
            "processed-twitter-sentiments-" + twitter_cache_key,
            result,
            ttl=timedelta(hours=24),
        )

        return UriResponse.get_single_data_response("twitter sentiment", result)

    @staticmethod
    async def process_keyword_conversation_insights(
        db: AsyncIOMotorDatabase, keyword: str, cache_key: str
    ) -> Any:
        processed_mentions_cache_key = "processed-twitter-posts-" + cache_key
        processed_mentions_data = await KeywordService.get_cached_data(
            db, processed_mentions_cache_key
        )

        if not processed_mentions_data:
            return UriResponse.get_single_data_response("No mentions data", None)

        # Extract tweets for analysis
        tweets = processed_mentions_data.get("posts_data", [])

        # Limit tweets for AI analysis (e.g., top 50 by engagement)
        # Generate AI-driven insights
        ai_insights = await KeywordService.analyze_keyword_conversations(
            keyword, tweets[:50]
        )

        result = {
            "ai_insights": ai_insights,  # Convert Pydantic model to dict
        }

        return UriResponse.get_single_data_response("keyword conversation", result)

    @staticmethod
    async def get_tweet_optimization_suggestions(
        db: AsyncIOMotorDatabase, cache_key: str
    ) -> Any:
        # Retrieve cached data or process raw Twitter data
        processed_posts_cache_key = "processed-twitter-posts-" + cache_key
        processed_posts_cache_data = await KeywordService.get_cached_data(
            db, processed_posts_cache_key
        )

        if not processed_posts_cache_data:
            return UriResponse.get_single_data_response(
                "tweet optimization", {"error": "No historical data available."}
            )

        # Extract posts for analysis
        posts = processed_posts_cache_data.get("posts_data", [])

        # Limit data to the top 50 tweets for analysis
        top_posts = sorted(
            posts,
            key=lambda x: (x["retweets"] + x["likes"] + x["replies"]),
            reverse=True,
        )[:50]

        # Use AI to generate suggestions
        ai_suggestions = KeywordService.optimize_tweets(top_posts)

        # Format Response
        result = {
            "historical_tweets_analyzed": len(top_posts),
            "optimization_suggestions": ai_suggestions,
        }

        return UriResponse.get_single_data_response("tweet optimization", result)

    @staticmethod
    async def analyze_keyword_conversations(
        keyword: str, tweets: List[dict]
    ) -> KeywordConversationInsight:
        """
        Analyze tracked keyword conversations and provide actionable insights.

        Args:
            keyword (str): The tracked keyword being analyzed.
            tweets (List[dict]): List of tweets mentioning the keyword.

        Returns:
            KeywordConversationInsight: Structured insights and recommendations.
        """
        # Prepare formatted data for the prompt
        formatted_tweets = [
            f"Tweet: {tweet['text']}, Engagements: {tweet['likes'] + tweet['retweets'] + tweet['replies']}, "
            f"Sentiment: {tweet.get('sentiment', {}).get('sentiment', 'neutral')}"
            for tweet in tweets
        ]

        # Define the prompt
        prompt = f"""
        You are an advanced analytics expert. Analyze the following tweets mentioning the keyword "{keyword}" and provide structured insights:
        1. Key conversation trends (topics, sentiments, engagement patterns) in the tweets and provide the justification from the tweets.
        2. Actionable business recommendations based on trends in the tweets and provide the justification from the tweets.
        3. Emotional tones expressed in the tweets with their respective scores distributed in 100 percent, (e.g., joy 20 percent, anger 40 percent, sadness 40 percent, etc.) based on the tweets.
        4. **Content Themes**: Highlight recurring themes or topics within the conversation tweets provided and provide the justification from the tweets.
        5. **Engagement Drivers**: Identify factors that are driving engagement in the conversation tweets provided and provide the justification from the tweets.
        6. Opportunities to improve engagement and visibility based on the tweets and provide the justification from the tweets.
        7. **Conversation Velocity**: Analyze the rate at which the conversation is growing or declining, and highlight peak times in the tweets.
        8. **Weekly (between 3 to 5 days) Campaign Calendar**: Based on the trends, provide a detailed weekly campaign calendar to guide future posts:
            - **Topic**: The focus or theme of the post.
            - **Title**: A suggested headline or message for the post.
            - **Post**: The content or core idea of the post.
            - **Media Type**: The recommended media type (e.g., image, video, infographic).
            - **Day of the Week**: The suggested day to post.
            - **Post Time**: The ideal time to post based on conversation activity.
            - **Hashtags**: Suggested hashtags to use.
            - **Mentions**: (Optional) Key accounts to mention.
            - **Target Audience Countries**: (Optional) Geographical target audience.
            - **Post Justification**: Justify why this post is relevant and aligned with trends.

        Tweets:
        {formatted_tweets[:50]}  # Limit to 50 tweets
        """

        # Pass the prompt to the AI model
        model = AIService.build_ai_model(
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}",
                }
            ]
        )

        # Parse the AI's structured response to match the model
        response = (
            await AIService.structured_chat_completion(
                model, KeywordConversationInsight
            )
        ).dict()

        ai_report_content = response["choices"][0]["message"]["parsed"]
        return ai_report_content

    @staticmethod
    async def get_keyword_sentiment_over_time(
        db: AsyncIOMotorDatabase,
        web_cache_key: str,
        twitter_cache_key: Optional[str] = None,
        source_filter: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get combined keyword sentiment data over time for web and Twitter, with optional filtering by source.

        Args:
            db (AsyncIOMotorDatabase): AsyncIOMotorDatabase connection.
            web_cache_key (str): Cache key for web keyword sentiment data.
            twitter_cache_key (str): Cache key for Twitter keyword sentiment data.
            source_filter (Optional[str]): Filter for "web", "twitter", or None for all sources.

        Returns:
            Dict[str, Any]: Sentiment data grouped by date.
        """
        # Fetch cached sentiment data for web and Twitter
        web_sentiment_data = (
            await KeywordService.get_cached_data(db, web_cache_key)
        ).get("sentiment", [])

        twitter_sentiment_data = (
            await KeywordService.get_cached_data(db, twitter_cache_key)
        ).get("sentiment", [])

        # Normalize Twitter data to match web data structure
        normalized_twitter_data = [
            {
                "author": item.get("author"),
                "comment": item.get("comment"),
                "timestamp": item.get("timestamp"),
                "image": item.get("image"),
                "website": "twitter.com",  # Add a constant website value for Twitter
                "sentiment": item.get("sentiment"),
            }
            for item in twitter_sentiment_data
        ]

        # Combine or filter sources based on source_filter
        combined_data = []
        if source_filter == "web":
            combined_data = web_sentiment_data
        elif source_filter == "twitter":
            combined_data = normalized_twitter_data
        else:
            combined_data = web_sentiment_data + normalized_twitter_data

        # Group sentiments by date
        sentiment_by_date: dict = defaultdict(
            lambda: {"positive": 0, "negative": 0, "neutral": 0}
        )
        for item in combined_data:
            date_str = item.get("timestamp")
            sentiment = item.get("sentiment", {}).get("sentiment", "neutral")
            if date_str:
                parsed_date = DateHelper.parse_date(date_str)

            if parsed_date:
                sentiment_by_date[parsed_date][sentiment] += 1

        # Format grouped data for charting
        formatted_data = sorted(
            [
                {
                    "date": date.isoformat(),
                    "positive": counts["positive"],
                    "negative": counts["negative"],
                    "neutral": counts["neutral"],
                }
                for date, counts in sentiment_by_date.items()
            ],
            key=lambda x: x["date"],
        )

        return UriResponse.get_single_data_response(
            "sentiment over time", formatted_data
        )

    @staticmethod
    async def fetch_cleaned_keyword_posts(
        db: AsyncIOMotorDatabase, keyword_cache_key: str
    ) -> dict:
        """
        Fetch and clean keyword posts from the database.
        """
        # Fetch raw posts from the database
        raw_posts = await KeywordService.get_cached_data(db, keyword_cache_key)
        posts = raw_posts.get("posts_data", [])

        # Clean the posts
        cleaned_posts = []

        # templated, implement actual posts/insight
        for post in posts:
            cleaned_post = {
                "id": post.get("id"),
                "text": post.get("text"),
                "author": post.get("author"),
                "timestamp": post.get("timestamp"),
                "image": post.get("image"),
                "website": post.get("website"),
                "likes": post.get("likes"),
            }
            cleaned_posts.append(cleaned_post)

        return UriResponse.get_single_data_response("keyword posts", cleaned_posts)

    @staticmethod
    async def optimize_tweets(tweets: List[dict]) -> TweetOptimizationResponse:
        """
        Use OpenAI to analyze historical tweet data and suggest optimizations.

        Args:
            tweets (List[dict]): List of historical tweets with engagement data.

        Returns:
            TweetOptimizationResponse: AI-generated suggestions for tweet optimization.
        """
        formatted_tweets = [
            f"Tweet: {tweet['text']}, Engagements: {tweet['likes'] + tweet['retweets'] + tweet['replies']}"
            for tweet in tweets
        ]

        prompt = AIChiefAnalystPrompt.TWEET_OPTIMIZATION_PROMPT.value.format(
            tweets="\n".join(formatted_tweets)
        )

        model = AIService.build_ai_model(
            messages=[{"role": "user", "content": prompt}],
        )

        return await AIService.structured_chat_completion(
            model, TweetOptimizationResponse
        )

    @staticmethod
    async def __process_influencers_rating(influencers: list) -> dict:
        # Count occurrences of each influencer (as a JSON string)
        influencer_freq = Counter(
            json.dumps(influencer, sort_keys=True) for influencer in influencers
        )

        # Sort influencers by frequency (descending)
        sorted_influencers = sorted(
            influencer_freq.items(), key=lambda x: x[1], reverse=True
        )

        # Convert JSON strings back to dictionaries
        sorted_influencers = [(json.loads(k), v) for k, v in sorted_influencers]

        result = {"top_influencers": sorted_influencers[:5]}
        return result
