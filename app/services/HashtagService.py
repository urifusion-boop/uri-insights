from collections import Counter
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.domain.enums import ai_prompt
from app.domain.enums.reportgeneration_enum import ReportGenerationTypeEnum as FeatName
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.models import chat_model
from app.domain.models.chat_model import (
    HashtagConversationInsight,
    HashtagInsightSummary,
)
from app.domain.responses.uri_response import UriResponse
from app.repository.CacheRepository import CacheRepository
from app.repository.InfluencerRepository import InfluencerRepository
from app.services.AIService import AIService
from app.services.EmbeddingService import EmbeddingService
from app.services.GoogleService import GoogleService
from app.services.InstagramHashtagService import InstagramHashtagService


class HashtagService:
    # --- Private helpers ---
    @staticmethod
    def _format_cache_key(hashtag_cache_key: str) -> str:
        return (
            hashtag_cache_key
            if hashtag_cache_key.startswith("hashtag-")
            else f"hashtag-{hashtag_cache_key}"
        )

    @staticmethod
    def _build_chat_model(prompt: str) -> chat_model.ChatModel:
        return chat_model.ChatModel(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

    @staticmethod
    async def _get_uri_instagram_token(db: AsyncIOMotorDatabase) -> str:
        response = await InfluencerRepository.get_influencer_by_social_user_id(
            db, settings.URI_INSTAGRAM_ID
        )
        influencer = response.get("responseData", {})
        return influencer.get("token")

    @staticmethod
    async def _get_instagram_user_id(
        db: AsyncIOMotorDatabase, platform: str, token: Optional[str] = None
    ) -> Optional[str]:
        if token:
            response = await InfluencerRepository.get_influencer_by_token_and_platform(
                db, token, platform
            )
            influencer = response.get("responseData", {})
            return influencer.get("social_user_id")
        return None

    @staticmethod
    async def _get_cached_data(
        db: AsyncIOMotorDatabase, cache_key: str
    ) -> Optional[dict]:
        return await CacheRepository.get_cache(db, cache_key)

    @staticmethod
    async def _set_cached_data(
        db: AsyncIOMotorDatabase, cache_key: str, data: Any, ttl: int = 12
    ) -> None:
        await CacheRepository.set_cache(
            db, cache_key, data, timedelta(hours=float(ttl))
        )

    @staticmethod
    async def _compute_post_distribution(
        db: AsyncIOMotorDatabase, hashtag_cache_key: str
    ) -> dict:
        posts_response = await HashtagService.fetch_cleaned_hashtag_posts(
            db=db, hashtag_cache_key=hashtag_cache_key
        )
        posts = posts_response.get("responseData", [])
        post_distribution_list = [post.get("media_type", "") for post in posts]
        post_distribution = Counter(post_distribution_list)
        return dict(post_distribution)

    # --- Public methods ---
    @staticmethod
    async def search(
        hashtag: str,
        db: AsyncIOMotorDatabase,
        background_tasks: Optional[BackgroundTasks] = None,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tracks a hashtag by checking the database first, then fetching from Meta API if necessary."""
        hashtag_cache_key = HashtagService._format_cache_key(hashtag)
        try:
            cached_data = await HashtagService._get_cached_data(db, hashtag_cache_key)

            if cached_data:
                return UriResponse.get_single_data_response("hashtag", cached_data)

            instagram_token = (
                access_token or await HashtagService._get_uri_instagram_token(db)
            )

            instagram_user_id = await HashtagService._get_instagram_user_id(
                db=db, token=access_token, platform=PostPlatformEnum.INSTAGRAM.value
            )

            response = await InstagramHashtagService.track_hashtag(
                hashtag, db, instagram_token, instagram_user_id
            )

            data = response.get("responseData", {})

            if data:
                await CacheRepository.set_cache(
                    db, hashtag_cache_key, data, ttl=timedelta(hours=12)
                )
                if background_tasks:
                    background_tasks.add_task(
                        HashtagService.trigger_hashtag_data_embedding,
                        db,
                        hashtag_cache_key,
                        hashtag,
                        data,
                    )
                return UriResponse.get_single_data_response(
                    "hashtag", {**data, "key": hashtag_cache_key}
                )

            return UriResponse.get_single_data_response("hashtag", None)

        except HTTPException as e:
            print(f"HTTPException in search: {e}")
            error_message = e.detail
            raise Exception(
                f"Failed to search for hashtag '{hashtag}': {error_message}"
            )

    @staticmethod
    async def fetch_cleaned_hashtag_posts(
        db: AsyncIOMotorDatabase, hashtag_cache_key: str
    ) -> dict:
        if not hashtag_cache_key:
            return UriResponse.get_single_data_response(
                "ai post report", None, code=400, message="Missing hashtag_cache_key"
            )

        hashtag_cache_key = HashtagService._format_cache_key(hashtag_cache_key)
        cleaned_hashtag_posts_cache_key = f"cleaned_hashtag_posts_{hashtag_cache_key}"

        cleaned_hashtag_posts = await HashtagService._get_cached_data(
            db, cleaned_hashtag_posts_cache_key
        )

        if cleaned_hashtag_posts:
            return UriResponse.get_single_data_response(
                "posts ai report", cleaned_hashtag_posts
            )

        cached_data = await HashtagService._get_cached_data(db, hashtag_cache_key)

        if not cached_data:
            return UriResponse.get_single_data_response("posts ai report", None)

        posts = [
            {
                k: v
                for k, v in post.items()
                if k not in ["permalink", "media_url", "children"]
            }
            for post in cached_data.get("media", [])
        ]

        await HashtagService._set_cached_data(
            db, cleaned_hashtag_posts_cache_key, posts
        )

        print(f"✅ Processed {len(posts)} posts.")
        return UriResponse.get_single_data_response("ai posts", posts)

    @staticmethod
    async def fetch_post_report(
        db: AsyncIOMotorDatabase, hashtag_cache_key: str
    ) -> dict:
        if not hashtag_cache_key:
            return UriResponse.get_single_data_response(
                "ai post report", None, code=400, message="Missing hashtag_cache_key"
            )

        hashtag_cache_key = HashtagService._format_cache_key(hashtag_cache_key)
        post_report_cache_key = f"hashtag-ai-post-report-{hashtag_cache_key}"

        cached_report = await HashtagService._get_cached_data(db, post_report_cache_key)
        if cached_report and cached_report.get("related_hashtags"):
            return UriResponse.get_single_data_response("ai post report", cached_report)

        cached_data = await HashtagService._get_cached_data(db, hashtag_cache_key)
        if not cached_data:
            return UriResponse.get_single_data_response("posts ai report", None)

        cleaned_posts_response = await HashtagService.fetch_cleaned_hashtag_posts(
            db, hashtag_cache_key
        )
        posts = cleaned_posts_response.get("responseData")

        prompt = ai_prompt.AIChiefAnalystPrompt.HASHTAG_POST_INSIGHTS_SUMMARY_REQUEST.value.format(
            posts=posts
        )
        model = HashtagService._build_chat_model(prompt)

        try:
            ai_report = (
                await AIService.structured_chat_completion(model, HashtagInsightSummary)
            ).dict()
            parsed_report = ai_report["choices"][0]["message"]["parsed"]

            await CacheRepository.set_cache(
                db, post_report_cache_key, parsed_report, ttl=timedelta(hours=12)
            )
            return UriResponse.get_single_data_response(
                "ai media report", parsed_report
            )

        except (KeyError, AttributeError) as e:
            print(f"Error parsing AI response: {e}")
            return UriResponse.get_single_data_response(
                "ai media report", None, code=500, message="Failed to parse AI response"
            )

    @staticmethod
    async def fetch_sentiment_analysis(
        db: AsyncIOMotorDatabase, hashtag_cache_key: str
    ):
        hashtag_cache_key = HashtagService._format_cache_key(hashtag_cache_key)
        sentiment_cache_key = f"sentiment_{hashtag_cache_key}"

        cached_result = await HashtagService._get_cached_data(db, sentiment_cache_key)

        if cached_result:
            return UriResponse.get_single_data_response(
                "hashtag sentiment analysis", cached_result
            )

        cleaned_posts = (
            await HashtagService.fetch_cleaned_hashtag_posts(db, hashtag_cache_key)
        ).get("responseData", {})

        sentiment_result = await GoogleService.analyze_comments_sentiment(
            cleaned_posts, "caption"
        )

        sentiment_map = {
            s["id"]: s["sentiment"]
            for s in sentiment_result.get("comments_with_sentiment", [])
        }
        post_sentiments = [
            {
                "timestamp": post.get("timestamp"),
                **sentiment_map.get(post["id"], {"sentiment": "neutral", "score": 0}),
            }
            for post in cleaned_posts
        ]

        final_sentiment_results = {
            "post_sentiments": post_sentiments,
            "sentiment_summary": sentiment_result["sentiment_summary"],
            "top_positive_comment": sentiment_result["top_positive_comment"],
            "top_negative_comment": sentiment_result["top_negative_comment"],
        }

        await HashtagService._set_cached_data(
            db, sentiment_cache_key, final_sentiment_results
        )

        return UriResponse.get_single_data_response(
            "hashtag sentiment analysis", final_sentiment_results
        )

    @staticmethod
    async def analyze_hashtag_conversations(
        db: AsyncIOMotorDatabase, hashtag: str
    ) -> HashtagConversationInsight:
        hashtag_cache_key = HashtagService._format_cache_key(hashtag)
        analyzed_conversation_cache_key = f"analyzed_conversation_{hashtag_cache_key}"

        cached_result = await HashtagService._get_cached_data(
            db, analyzed_conversation_cache_key
        )

        if cached_result:
            return UriResponse.get_single_data_response(
                "ai post conversation insight", cached_result
            )

        cached_data = await HashtagService._get_cached_data(db, hashtag_cache_key)

        if cached_data:
            cleaned_posts_response = await HashtagService.fetch_cleaned_hashtag_posts(
                db, hashtag_cache_key
            )
            posts = cleaned_posts_response.get("responseData")

            prompt = ai_prompt.AIChiefAnalystPrompt.HASHTAG_CONVERSATION_INSIGHTS_REQUEST.value.format(
                hashtag=hashtag, posts=posts
            )
            model = HashtagService._build_chat_model(prompt)
            try:
                response = (
                    await AIService.structured_chat_completion(
                        model, HashtagConversationInsight
                    )
                ).dict()
                parsed_response = response["choices"][0]["message"]["parsed"]
                await HashtagService._set_cached_data(
                    db, analyzed_conversation_cache_key, parsed_response
                )
                return UriResponse.get_single_data_response(
                    "ai post conversation insight", parsed_response
                )
            except (KeyError, AttributeError) as e:
                print(f"Error parsing conversation insight: {e}")
                return UriResponse.get_single_data_response(
                    "ai post conversation insight",
                    None,
                    code=500,
                    message="Failed to parse AI conversation insight",
                )

        return UriResponse.get_single_data_response(
            "ai post conversation insight", None
        )

    @staticmethod
    async def trigger_hashtag_data_embedding(
        db: AsyncIOMotorDatabase,
        hashtag_cache_key: str,
        hashtag: str,
        data: Dict[str, Any],
    ):
        posts = (
            await HashtagService.fetch_cleaned_hashtag_posts(db, hashtag_cache_key)
        ).get("responseData", [{}])
        await EmbeddingService.bulk_process_items(
            db=db, feature_name=FeatName.HASHTAG_TRACKING, items=posts, hashtag=hashtag
        )
        await EmbeddingService.process_summary_data(
            db=db, feature=FeatName.HASHTAG_TRACKING, summary_data=data, hashtag=hashtag
        )
