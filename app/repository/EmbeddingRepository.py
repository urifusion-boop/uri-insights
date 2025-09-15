import asyncio
from typing import Any, Dict, List, Optional, Union
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.operations import SearchIndexModel
from app.core.helpers.embedding_helper import EmbeddingHelper
from app.domain.enums.embedding_enum import EmbeddingModelEnum
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.responses.uri_response import UriResponse
from app.schemas import (
    AccountPostEmbedding,
    HashtagPostEmbedding,
    HashtagSummaryEmbeddingModel,
)


class EmbeddingRepository:
    COLLECTION_NAME = "embeddings"
    INDEX_NAME = "embedding_index"

    @staticmethod
    def get_collection(db: AsyncIOMotorDatabase) -> AsyncIOMotorCollection:
        return db[EmbeddingRepository.COLLECTION_NAME]

    @staticmethod
    def _construct_embedding_filters_query(
        user_id: Optional[str] = None,
        platform: Optional[PostPlatformEnum] = None,
        influencer_id: Optional[str] = None,
        hashtag: Optional[str] = None,
    ) -> Dict[str, Any]:
        query: Dict[str, Any] = {}

        if user_id:
            query["user_id"] = user_id
        if platform:
            query["platform"] = platform
        if influencer_id:
            query["influencer_id"] = influencer_id
        if hashtag:
            query["hashtag"] = hashtag

        return query

    @staticmethod
    async def create_embedding(
        db: AsyncIOMotorDatabase,
        embedding_data: Union[
            HashtagPostEmbedding, AccountPostEmbedding, HashtagSummaryEmbeddingModel
        ],
    ) -> dict:
        collection = EmbeddingRepository.get_collection(db)
        embedding_dict = embedding_data.model_dump()
        await collection.replace_one(
            {"embedding": embedding_dict["embedding"]},
            embedding_dict,
            upsert=True,
        )
        return UriResponse.create_response("embedding document", embedding_dict)

    @staticmethod
    async def create_multiple_embeddings(
        db: AsyncIOMotorDatabase,
        documents: List[Dict],
    ) -> dict:
        if not documents:
            return UriResponse.create_response("inserted documents")

        collection = EmbeddingRepository.get_collection(db)
        result = await collection.insert_many(documents, ordered=False)
        return UriResponse.create_response(
            "inserted documents", {"inserted_ids": result.inserted_ids}
        )

    @staticmethod
    async def get_by_filters(
        db: AsyncIOMotorDatabase,
        user_id: Optional[str] = None,
        platform: Optional[PostPlatformEnum] = None,
        influencer_id: Optional[str] = None,
        hashtag: Optional[str] = None,
    ) -> dict:
        query = EmbeddingRepository._construct_embedding_filters_query(
            user_id=user_id,
            platform=platform,
            influencer_id=influencer_id,
            hashtag=hashtag,
        )
        collection = EmbeddingRepository.get_collection(db)
        cursor = collection.find(query)
        documents = await cursor.to_list(length=None)
        return UriResponse.create_response("user embeddings", documents)

    @staticmethod
    async def delete_by_id(
        db: AsyncIOMotorDatabase,
        embedding_id: str,
    ) -> dict:
        collection = EmbeddingRepository.get_collection(db)
        result = await collection.delete_one({"embedding_id": embedding_id})
        return UriResponse.create_response(
            "deleted document count", {"deleted_count": result.deleted_count}
        )

    @staticmethod
    async def exists(
        db: AsyncIOMotorDatabase,
        embedding_id: str,
    ) -> bool:
        collection = EmbeddingRepository.get_collection(db)
        count = await collection.count_documents(
            {"embedding_id": embedding_id}, limit=1
        )
        return count > 0

    @staticmethod
    async def vector_search(
        db: AsyncIOMotorDatabase,
        query_str: str,
        top_k: int = 10,
        candidates: int = 100,
        filter_query: Dict = {},
        results_filter: Dict = {},
    ) -> dict:
        collection = EmbeddingRepository.get_collection(db)
        embedding = EmbeddingHelper.generate_embedding(
            query_str, EmbeddingModelEnum.ADA
        )
        if not embedding:
            raise ValueError("Embedding generation failed")
        pipeline = [
            {
                "$vectorSearch": {
                    "queryVector": embedding,
                    "path": "embedding",
                    "numCandidates": candidates,
                    "limit": top_k,
                    "index": EmbeddingRepository.INDEX_NAME,
                    "filter": filter_query,
                }
            },
            {"$project": results_filter},
        ]
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=top_k)

        return UriResponse.get_single_data_response("vector search results", results)

    @staticmethod
    async def create_vector_index(db: AsyncIOMotorDatabase):
        collection = EmbeddingRepository.get_collection(db)
        vector_index_name = EmbeddingRepository.INDEX_NAME
        index_info = await collection.index_information()
        if vector_index_name in index_info:
            print(f"Vector index '{vector_index_name}' already exists.")
            return

        # MongoDB Atlas style vector index creation — adjust based on your deployment
        try:
            search_index = SearchIndexModel(
                definition={
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": 1536,
                            "similarity": "cosine",
                        },
                        {"type": "filter", "path": "hashtag"},
                        {"type": "filter", "path": "embedding_type"},
                        {"type": "filter", "path": "social_user_id"},
                        {"type": "filter", "path": "platform"},
                    ]
                },
                name=EmbeddingRepository.INDEX_NAME,
                type="vectorSearch",
            )
            await collection.create_search_index(model=search_index)
            await EmbeddingRepository.wait_until_index_ready(
                collection, vector_index_name, 100
            )
        except TimeoutError as e:
            print(e)
        except Exception as e:
            print(f"Failed to create vector index: {e}")

    @staticmethod
    async def wait_until_index_ready(
        collection: AsyncIOMotorCollection, index_name: str, timeout: int = 60
    ):
        print(f"⏳ Waiting for vector index '{index_name}' to become queryable...")

        for _ in range(timeout // 5):  # Check every 5s up to 60s
            indexes = await collection.list_search_indexes().to_list(length=None)
            index = next((idx for idx in indexes if idx["name"] == index_name), None)
            if index and index.get("queryable", False):
                print(f"✅ Vector index '{index_name}' is ready for querying.")
                return True
            await asyncio.sleep(5)

        raise TimeoutError(
            f"❌ Timeout: Index '{index_name}' not ready after {timeout} seconds."
        )

    @staticmethod
    async def delete_vector_index(db: AsyncIOMotorDatabase):
        collection = EmbeddingRepository.get_collection(db)
        try:
            await collection.drop_search_index(EmbeddingRepository.INDEX_NAME)
            print(
                f"✅ Vector index '{EmbeddingRepository.INDEX_NAME}' has been deleted."
            )
        except Exception as e:
            print(
                f"❌ Failed to delete vector index '{EmbeddingRepository.INDEX_NAME}': {e}"
            )
