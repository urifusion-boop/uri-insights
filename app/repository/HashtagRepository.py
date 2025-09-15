from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from app.domain.responses.uri_response import UriResponse
from app import schemas


class HashtagRepository:
    @staticmethod
    async def create_hashtag(
        db: AsyncIOMotorDatabase, hashtag: schemas.HashtagCreate
    ) -> Dict[str, Any]:
        db_hashtag = hashtag.dict()
        db_hashtag["_id"] = str(ObjectId())
        db_hashtag["createdAt"] = datetime.utcnow().isoformat()
        db_hashtag["updatedAt"] = datetime.utcnow().isoformat()

        await db["hashtags"].insert_one(db_hashtag)

        return UriResponse.create_response(
            "hashtag", schemas.Hashtag(**db_hashtag).dict()
        )

    @staticmethod
    async def get_hashtag_by_word(
        db: AsyncIOMotorDatabase, keyword: str
    ) -> Optional[Dict[str, Any]]:
        db_hashtag = await db["hashtags"].find_one({"keyword": keyword.lower()})
        if not db_hashtag:
            return None
        return schemas.Hashtag(**db_hashtag).dict()

    @staticmethod
    async def get_hashtag_by_id(
        db: AsyncIOMotorDatabase, hashtag_id: str
    ) -> Optional[Dict[str, Any]]:
        db_hashtag = await db["hashtags"].find_one({"_id": hashtag_id})
        if not db_hashtag:
            return None
        return schemas.Hashtag(**db_hashtag).dict()

    @staticmethod
    async def update_hashtag(
        db: AsyncIOMotorDatabase, hashtag: schemas.HashtagUpdate
    ) -> Optional[Dict[str, Any]]:
        db_hashtag = hashtag.dict(exclude_unset=True)
        db_hashtag["updatedAt"] = datetime.utcnow().isoformat()

        result = await db["hashtags"].update_one(
            {"_id": hashtag._id}, {"$set": db_hashtag}
        )

        if result.matched_count == 0:
            return None

        updated = await HashtagRepository.get_hashtag_by_id(db, hashtag._id)
        return updated

    @staticmethod
    async def delete_hashtag(
        db: AsyncIOMotorDatabase, hashtag_id: str
    ) -> Dict[str, Any]:
        result = await db["hashtags"].delete_one({"_id": hashtag_id})
        return UriResponse.delete_response("hashtag", result.deleted_count > 0)
