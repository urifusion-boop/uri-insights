"""
Family of functions that handle the preprocessing and document construction of embeddings.
These functions support all embedding-required data types and implement mini-factories for dispatching the correct logic.
"""

from datetime import datetime
from typing import Callable, Dict, List, Optional

from app.domain.enums.embedding_enum import EmbeddingTypeEnum
from app.domain.enums.reportgeneration_enum import ReportGenerationTypeEnum as FeatName
from app.domain.enums.socialmediapost_enum import PostPlatformEnum


class EmbeddingStrategy:
    # =======================
    # PREPROCESSING FUNCTIONS
    # =======================
    @staticmethod
    def preprocess_hashtag_item(item: Dict) -> str:
        return item.get("caption", "")

    @staticmethod
    def preprocess_account_item(item: Dict, platform: PostPlatformEnum) -> str:
        return (
            item.get("caption", "")
            if platform == PostPlatformEnum.INSTAGRAM
            else item.get("content", "")
        )

    _PREPROCESSOR_MAP: Dict[FeatName, Callable[..., str]] = {
        FeatName.HASHTAG_TRACKING: preprocess_hashtag_item,
        FeatName.ACCOUNT_TRACKING: preprocess_account_item,
    }

    @staticmethod
    def preprocess_item_for_embedding(
        feature: FeatName, item: Dict, platform: Optional[PostPlatformEnum] = None
    ) -> str:
        preprocessor = EmbeddingStrategy._PREPROCESSOR_MAP.get(feature)
        if not preprocessor:
            raise ValueError(f"No preprocessor found for feature: {feature}")
        return preprocessor(item, platform) if platform else preprocessor(item)

    # =======================
    # DOCUMENT BUILDER FUNCTIONS
    # =======================

    @staticmethod
    def build_hashtag_document(
        item: Dict, embedding: List[float], hashtag: Optional[str] = None
    ) -> Dict:
        if hashtag:
            return {
                "hashtag": hashtag.lower(),
                "caption": item.get("caption", ""),
                "timestamp": item.get("timestamp"),
                "like_count": item.get("like_count"),
                "comments_count": item.get("comments_count"),
                "media_type": item.get("media_type"),
                "media_url": item.get("media_url"),
                "permalink": item.get("permalink"),
                "embedding": embedding,
                "embedding_type": EmbeddingTypeEnum.HASHTAG_TRACKING_EMBEDDING.value,
            }
        raise ValueError("Hashtag not provided to build embedding document")

    @staticmethod
    def build_instagram_document(
        item: Dict, embedding: List[float], social_user_id: str
    ) -> Dict:
        like_count = item.get("like_count", 0)
        comment_count = item.get("comments_count", 0)
        return {
            "social_user_id": social_user_id,
            "content": item.get("caption", ""),
            "post_time": item.get("timestamp"),
            "comment_count": comment_count,
            "like_count": like_count,
            "engagement_count": like_count + comment_count,
            "media_type": item.get("media_type"),
            "embedding": embedding,
            "embedding_type": EmbeddingTypeEnum.ACCOUNT_TRACKING_EMBEDDING.value,
            "platform": PostPlatformEnum.INSTAGRAM.value,
        }

    @staticmethod
    def build_facebook_document(
        item: Dict, embedding: List[float], social_user_id: str
    ) -> Dict:
        return {
            "social_user_id": social_user_id,
            **item,
            "embedding": embedding,
            "embedding_type": EmbeddingTypeEnum.ACCOUNT_TRACKING_EMBEDDING.value,
            "platform": PostPlatformEnum.FACEBOOK.value,
        }

    @staticmethod
    def build_linkedin_document(
        item: Dict, embedding: List[float], social_user_id: str
    ) -> Dict:
        return {
            "social_user_id": social_user_id,
            **item,
            "embedding": embedding,
            "embedding_type": EmbeddingTypeEnum.ACCOUNT_TRACKING_EMBEDDING.value,
            "platform": PostPlatformEnum.LINKEDIN.value,
        }

    _PLATFORM_DOC_BUILDERS: Dict[PostPlatformEnum, Callable] = {
        PostPlatformEnum.INSTAGRAM: build_instagram_document,
        PostPlatformEnum.FACEBOOK: build_facebook_document,
        PostPlatformEnum.LINKEDIN: build_linkedin_document,
    }

    @staticmethod
    def build_account_document(
        item: Dict,
        embedding: List[float],
        platform: Optional[PostPlatformEnum] = None,
        social_user_id: Optional[str] = None,
    ) -> Dict:
        if not embedding or not platform or not social_user_id:
            raise ValueError(
                "Insufficient data provided for building account tracking post embedding document"
            )
        builder = EmbeddingStrategy._PLATFORM_DOC_BUILDERS.get(platform)
        if not builder:
            raise ValueError(f"No document builder for platform: {platform}")
        return builder(item, embedding, social_user_id)

    # Factory method for document building
    _DOC_BUILDER_FACTORY: Dict[FeatName, Callable] = {
        FeatName.HASHTAG_TRACKING: build_hashtag_document,
        FeatName.ACCOUNT_TRACKING: build_account_document,
    }

    @staticmethod
    def build_embedding_document(
        feature: FeatName,
        item: Dict,
        embedding: List[float],
        hashtag: Optional[str] = None,
        platform: Optional[PostPlatformEnum] = None,
        social_user_id: Optional[str] = None,
    ) -> Dict:
        builder = EmbeddingStrategy._DOC_BUILDER_FACTORY.get(feature)
        if not builder:
            raise ValueError(f"No document builder found for feature: {feature}")

        if feature == FeatName.HASHTAG_TRACKING:
            return builder(item, embedding, hashtag)
        if feature == FeatName.ACCOUNT_TRACKING:
            return builder(item, embedding, platform, social_user_id)

        raise ValueError(f"Invalid feature {feature} for document construction")

    # =======================
    # Summary data refers to other relevant data gotten from the process of hashtag or account tracking
    # which are not posts themselves but are also instrumental in providing rich context to our generation process
    # This section handles summary data for both hashtag and account tracking
    # =======================

    @staticmethod
    def preprocess_hashtag_summary_data(summary_data: Dict) -> str:
        count = summary_data.get("count", 0)
        hashtags = summary_data.get("hashtag_mention_frequency", [])
        top_hashtags = sorted(hashtags, key=lambda h: h["count"], reverse=True)[:10]
        hashtag_list = [f"{h['hashtag']} ({h['count']})" for h in top_hashtags]
        summary_text = (
            f"Analyzed {count} number of posts. Top hashtags used: "
            + ", ".join(hashtag_list)
            + "."
        )

        post_types = summary_data.get("post_type_distribution", [])
        if post_types:
            post_summary = ", ".join(
                [f"{p['media_type'].lower()}s: {p['count']}" for p in post_types]
            )
            summary_text += f" Post type distribution - {post_summary}."

        return summary_text

    @staticmethod
    def preprocess_account_summary_data(summary_data: Dict):
        # Stub: Implementation will depend on future structure of summary data
        pass

    _SUMMARY_PREPROCESSOR_MAP: Dict[FeatName, Callable[[Dict], str]] = {
        FeatName.HASHTAG_TRACKING: preprocess_hashtag_summary_data,
        FeatName.ACCOUNT_TRACKING: preprocess_account_summary_data,
    }

    @staticmethod
    def preprocess_summary_for_embedding(feature: FeatName, summary_data: Dict) -> str:
        preprocessor = EmbeddingStrategy._SUMMARY_PREPROCESSOR_MAP.get(feature)
        if not preprocessor:
            raise ValueError(f"No summary preprocessor found for feature: {feature}")
        return preprocessor(summary_data)

    @staticmethod
    def build_hashtag_summary_document(
        summary_data: Dict, embedding: List[float], hashtag: Optional[str]
    ) -> Dict:
        if hashtag:
            return {
                "hashtag": hashtag,
                "post_count": summary_data.get("count", 0),
                "post_type_distribution": summary_data.get(
                    "post_type_distribution", []
                ),
                "hashtag_mention_frequency": summary_data.get(
                    "hashtag_mention_frequency", []
                ),
                "embedding": embedding,
                "embedding_type": EmbeddingTypeEnum.HASHTAG_TRACKING_EMBEDDING.value,
            }
        raise ValueError("Hashtag not provided to build summary embedding document")

    @staticmethod
    def build_account_summary_document(
        summary_data: Dict,
        embedding: List[float],
        social_user_id: Optional[str] = None,
        platform: Optional[PostPlatformEnum] = None,
    ):
        # Stub builder for account tracking summary
        pass

    _SUMMARY_DOC_BUILDER_FACTORY: Dict[FeatName, Callable] = {
        FeatName.HASHTAG_TRACKING: build_hashtag_summary_document,
        FeatName.ACCOUNT_TRACKING: build_account_summary_document,
    }

    @staticmethod
    def build_summary_embedding_document(
        feature: FeatName,
        summary_data: Dict,
        embedding: List[float],
        hashtag: Optional[str] = None,
        social_user_id: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> Dict:
        builder = EmbeddingStrategy._SUMMARY_DOC_BUILDER_FACTORY.get(feature)
        if not builder:
            raise ValueError(
                f"No summary document builder found for feature: {feature}"
            )

        if feature == FeatName.HASHTAG_TRACKING:
            return builder(summary_data, embedding, hashtag)
        if feature == FeatName.ACCOUNT_TRACKING:
            return builder(summary_data, embedding, social_user_id, platform)

        raise ValueError(f"Invalid feature {feature} for summary document construction")
