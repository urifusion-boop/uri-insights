"""
This repository stores data as gotten directly from the 3rd party service Apollo.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import pymongo
import pymongo.errors

from app.domain.responses.uri_response import UriResponse


class ApolloRepository:
    COLLECTION_NAME = "apollo_data"

    @staticmethod
    async def create(db: AsyncIOMotorDatabase, data: dict) -> Dict:
        """
        Stores new Apollo data into the collection.
        """
        data["created_at"] = datetime.utcnow()

        result = await db[ApolloRepository.COLLECTION_NAME].insert_one(data)

        if not result.inserted_id:
            return UriResponse.custom_response("Failed to store Apollo data.", 500)

        data["id"] = str(result.inserted_id)
        return UriResponse.create_response("Apollo data stored", data)

    @staticmethod
    async def create_multiple(db: AsyncIOMotorDatabase, data: List[dict]):
        if not data:
            return {"error": "No data provided for insertion"}

        try:
            result = await db[ApolloRepository.COLLECTION_NAME].insert_many(data)
            return [str(_id) for _id in result.inserted_ids]
        except pymongo.errors.PyMongoError as e:
            print("Failed to insert multiple documents into Apollo collection.")
            raise Exception(str(e))

    @staticmethod
    async def get_by_id(db: AsyncIOMotorDatabase, apollo_data_id: str) -> Dict:
        if not ObjectId.is_valid(apollo_data_id):
            return UriResponse.custom_response("Invalid Apollo data ID")

        result = await db[ApolloRepository.COLLECTION_NAME].find_one(
            {"id": apollo_data_id}
        )

        if not result:
            return UriResponse.get_single_data_response("Apollo data", None)

        result["id"] = str(result["_id"])
        return UriResponse.get_single_data_response("Apollo data", result)

    @staticmethod
    async def get_phone_number_by_id(
        db: AsyncIOMotorDatabase, apollo_data_id: str
    ) -> Optional[str]:
        apollo_data = await ApolloRepository.get_by_id(db, apollo_data_id)
        if not apollo_data.get("status", False):
            return None
        return apollo_data.get("phone", "")

    @staticmethod
    async def delete(db: AsyncIOMotorDatabase, apollo_data_id: str) -> Dict:
        if not ObjectId.is_valid(apollo_data_id):
            return UriResponse.custom_response("Invalid Apollo data ID")

        result = await db[ApolloRepository.COLLECTION_NAME].delete_one(
            {"id": apollo_data_id}
        )

        return UriResponse.delete_response("Apollo data", result.deleted_count > 0)

    @staticmethod
    async def update(
        db: AsyncIOMotorDatabase, apollo_data_id: str, update_fields: dict
    ) -> Dict:
        if not ObjectId.is_valid(apollo_data_id):
            return UriResponse.custom_response("Invalid Apollo data ID")

        update_fields["updated_at"] = datetime.utcnow()

        result = await db[ApolloRepository.COLLECTION_NAME].update_one(
            {"id": apollo_data_id}, {"$set": update_fields}
        )

        if result.matched_count == 0:
            return UriResponse.custom_response("Apollo data not found.", 404)

        return await ApolloRepository.get_by_id(db, apollo_data_id)
