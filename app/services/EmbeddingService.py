from typing import Any, Dict, List, Optional
from app.core.helpers.embedding_helper import EmbeddingHelper
from app.domain.enums.embedding_enum import EmbeddingModelEnum, EmbeddingTypeEnum
from app.domain.enums.reportgeneration_enum import ReportGenerationTypeEnum as FeatName
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.responses.uri_response import UriResponse
from app.domain.strategies.EmbeddingStrategy import EmbeddingStrategy
from app.repository.EmbeddingRepository import EmbeddingRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas import (
    AccountPostEmbedding,
    HashtagPostEmbedding,
    HashtagSummaryEmbeddingModel,
)


class EmbeddingService:
    @staticmethod
    def process_item(
        feature_name: FeatName,
        item: Dict[str, Any],
        hashtag: Optional[str] = None,
        social_user_id: Optional[str] = None,
        platform: Optional[PostPlatformEnum] = None,
    ) -> Dict[str, Any]:
        text_to_embed = EmbeddingStrategy.preprocess_item_for_embedding(
            feature=feature_name, item=item, platform=platform
        )
        embedding = EmbeddingHelper.generate_embedding(
            text_to_embed, EmbeddingModelEnum.ADA
        )
        if not embedding:
            raise ValueError("Embedding generation failed")
        document_to_store = EmbeddingStrategy.build_embedding_document(
            feature=feature_name,
            item=item,
            embedding=embedding,
            hashtag=hashtag,
            platform=platform,
            social_user_id=social_user_id,
        )
        return document_to_store

    @staticmethod
    async def process_summary_data(
        db: AsyncIOMotorDatabase,
        feature: FeatName,
        summary_data: Dict[str, Any],
        hashtag: Optional[str] = None,
        social_user_id: Optional[str] = None,
    ):
        text_to_embed = EmbeddingStrategy.preprocess_summary_for_embedding(
            feature=feature, summary_data=summary_data
        )
        embedding = EmbeddingHelper.generate_embedding(
            text_to_embed, EmbeddingModelEnum.ADA
        )
        if not embedding:
            raise ValueError("Embedding generation failed")
        embedding_document = EmbeddingStrategy.build_summary_embedding_document(
            feature=feature,
            summary_data=summary_data,
            embedding=embedding,
            hashtag=hashtag,
            social_user_id=social_user_id,
        )
        created_embedding_doc = await EmbeddingRepository.create_embedding(
            db, HashtagSummaryEmbeddingModel(**embedding_document)
        )
        return created_embedding_doc

    @staticmethod
    async def bulk_process_items(
        db: AsyncIOMotorDatabase,
        feature_name: FeatName,
        items: List[Dict[str, Any]],
        hashtag: Optional[str] = None,
        social_user_id: Optional[str] = None,
        platform: Optional[PostPlatformEnum] = None,
    ):
        embedding_items_to_store = []
        for item in items:
            try:
                processed_item = EmbeddingService.process_item(
                    feature_name=feature_name,
                    item=item,
                    hashtag=hashtag,
                    social_user_id=social_user_id,
                    platform=platform,
                )
                parsed_item = None
                if feature_name == FeatName.HASHTAG_TRACKING:
                    parsed_item = HashtagPostEmbedding(**processed_item)
                elif feature_name == FeatName.ACCOUNT_TRACKING:
                    parsed_item = AccountPostEmbedding(**processed_item)
                if parsed_item:
                    embedding_items_to_store.append(parsed_item.dict(exclude_none=True))
                    print(
                        f"Item added to list for creation successfully: ",
                        parsed_item.dict(exclude_none=True),
                    )
            except Exception as e:
                print(f"Error processing item {item}: {e}")
        created_embedding_items = await EmbeddingRepository.create_multiple_embeddings(
            db, embedding_items_to_store
        )
        return created_embedding_items

    @staticmethod
    async def vector_search_hashtag_tracking_data(
        db: AsyncIOMotorDatabase, hashtag: str, user_message: str
    ):
        print(
            "----------------- RUNNING VECTOR SEARCH FOR HASHTAG TRACKING -----------------"
        )
        hashtag = EmbeddingHelper.prep_hashtag_for_embedding_search(hashtag)
        filter_query = {
            "hashtag": hashtag,
            "embedding_type": EmbeddingTypeEnum.HASHTAG_TRACKING_EMBEDDING.value,
        }

        results_filter = {
            "_id": 0,
            "hashtag": 1,
            "caption": 1,
            "timestamp": 1,
            "like_count": 1,
            "comments_count": 1,
            "media_type": 1,
        }

        try:
            results = await EmbeddingRepository.vector_search(
                db=db,
                query_str=user_message,
                filter_query=filter_query,
                results_filter=results_filter,
            )
            return results
        except Exception as e:
            print(
                "Exception occurred in performing hashtag tracking vector search: ", e
            )

    @staticmethod
    async def vector_search_account_tracking_data(
        db: AsyncIOMotorDatabase, social_user_id: str, platform: str, user_message: str
    ):
        print(
            "----------------- RUNNING VECTOR SEARCH FOR ACCOUNT TRACKING -----------------"
        )

        filter_query = {
            "social_user_id": social_user_id,
            "platform": platform,
            "embedding_type": EmbeddingTypeEnum.ACCOUNT_TRACKING_EMBEDDING.value,
        }

        results_filter = {
            "_id": 0,
            "platform": 1,
            "content": 1,
            "post_time": 1,
            "comment_count": 1,
            "engagement_count": 1,
            "media_type": 1,
        }

        try:
            results = (
                await EmbeddingRepository.vector_search(
                    db=db,
                    query_str=user_message,
                    filter_query=filter_query,
                    results_filter=results_filter,
                )
            ).get("responseData")
            return results
        except Exception as e:
            print(
                "Exception occurred in performing account tracking vector search: ", e
            )
