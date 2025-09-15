from typing import List, Optional
from bson import ObjectId
import openai

from app.domain.enums.embedding_enum import EmbeddingModelEnum


class EmbeddingHelper:
    @staticmethod
    def generate_embedding(
        text: str, model: EmbeddingModelEnum
    ) -> Optional[List[float]]:
        if text:
            try:
                return (
                    openai.embeddings.create(input=[text], model=model.value)
                    .data[0]
                    .embedding
                )
            except Exception as e:
                print("Exception occurred in generating embedding: ", e)
        return None

    @staticmethod
    def prep_hashtag_for_embedding_search(hashtag: str):
        if hashtag.startswith("#"):
            hashtag = hashtag.replace("#", "")
        return hashtag.lower()

    @staticmethod
    def generate_db_id():
        return str(ObjectId())
