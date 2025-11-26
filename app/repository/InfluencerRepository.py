from app.core.helpers.date_helper import DateHelper
from typing import Dict, Any, Optional, List, Union
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime

from app.domain.enums.account_enum import AccountTypeEnum
from app.domain.responses.uri_response import UriResponse
from app.domain.schemas import influencer_schema


class InfluencerRepository:
    @staticmethod
    async def create_influencer(
        db: AsyncIOMotorDatabase, influencer: influencer_schema.InfluencerCreate
    ) -> Dict[str, Any]:
        db_influencer = influencer.model_dump()
        db_influencer["influencer_id"] = str(ObjectId())
        db_influencer["connected"] = False

        await db["influencers"].insert_one(db_influencer)

        return UriResponse.create_response(
            "influencer",
            influencer_schema.Influencer(
                **db_influencer, validate_assignment=False
            ).model_dump(),
        )

    @staticmethod
    async def create_influencers(
        db: AsyncIOMotorDatabase, influencers: List[influencer_schema.InfluencerCreate]
    ) -> Dict[str, Any]:
        db_influencers = []

        for influencer in influencers:
            db_influencer = influencer
            db_influencer["influencer_id"] = str(ObjectId())
            db_influencer["connected"] = False
            db_influencer["createdAt"] = DateHelper.utc_now_iso()
            db_influencer["updatedAt"] = DateHelper.utc_now_iso()
            db_influencers.append(db_influencer)

        await db["influencers"].insert_many(db_influencers)

        inserted_influencers = [
            influencer_schema.Influencer(**db_influencer)
            for db_influencer in db_influencers
        ]

        return UriResponse.create_response("influencers", inserted_influencers)

    @staticmethod
    async def get_social_usernames_by_user(
        db: AsyncIOMotorDatabase, user_id: str
    ) -> List:
        influencers_cursor = db["influencers"].find(
            {"user_id": user_id}, {"social_username": 1, "social_platform": 1}
        )
        influencers = await influencers_cursor.to_list(length=None)

        return [
            (influencer["social_username"], influencer["social_platform"])
            for influencer in influencers
            if "social_username" in influencer and "social_platform" in influencer
        ]

    @staticmethod
    async def get_influencer_by_id(db: AsyncIOMotorDatabase, influencer_id: str) -> Any:
        db_influencer = await db["influencers"].find_one(
            {"influencer_id": influencer_id}
        )

        if not db_influencer:
            return UriResponse.get_single_data_response("influencer", None)

        return UriResponse.get_single_data_response(
            "influencer", influencer_schema.Influencer(**db_influencer).dict()
        )

    @staticmethod
    async def get_influencer_by_token_and_platform(
        db: AsyncIOMotorDatabase, token: str, platform: str
    ) -> Any:
        db_influencer = await db["influencers"].find_one(
            {"token": token, "social_platform": platform}
        )

        if not db_influencer:
            return UriResponse.get_single_data_response("influencer", None)

        return UriResponse.get_single_data_response(
            "influencer", influencer_schema.Influencer(**db_influencer).dict()
        )

    @staticmethod
    async def get_influencer_by_social_user_id(
        db: AsyncIOMotorDatabase, social_user_id: str
    ) -> dict:
        db_influencer = await db["influencers"].find_one(
            {"social_user_id": social_user_id}
        )
        if not db_influencer:

            return UriResponse.get_single_data_response("influencer", None)

        return UriResponse.get_single_data_response(
            "influencer", influencer_schema.Influencer(**db_influencer).dict()
        )

    @staticmethod
    async def get_influencers_by_filter(
        db: AsyncIOMotorDatabase,
        user_id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        location: Optional[str] = None,
        connected: Optional[bool] = None,
        account_type: Optional[AccountTypeEnum] = None,
        social_user_id: Optional[str] = None,
        social_username: Optional[str] = None,
        access_token: Optional[Union[str, Dict[str, Any]]] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Any:
        query: Dict[str, Any] = InfluencerRepository.__construct_filters_query(
            user_id=user_id,
            name=name,
            email=email,
            platforms=platforms,
            location=location,
            connected=connected,
            account_type=account_type,
            social_user_id=social_user_id,
            social_username=social_username,
            token=access_token,
        )

        total_influencers = await db["influencers"].count_documents(query)
        total_connected = await db["influencers"].count_documents(
            {**query, "connected": True}
        )
        total_disconnected = (
            total_influencers
            if query.get("connected") is False
            else total_influencers - total_connected
        )

        db_influencers_cursor = (
            db["influencers"].find(query).sort("createdAt", -1).skip(skip).limit(limit)
        )
        db_influencers = await db_influencers_cursor.to_list(length=None)

        influencers = [
            influencer_schema.Influencer(**influencer).dict()
            for influencer in db_influencers
        ]

        meta_data = {
            "totalConnected": 0 if query.get("connected") is False else total_connected,
            "totalDisconnected": total_disconnected,
        }

        return UriResponse.get_paged_data_response(
            "influencers", influencers, total_influencers, skip + 1, limit, meta_data
        )

    @staticmethod
    async def get_user_influencer_count_by_filters(
        db: AsyncIOMotorDatabase,
        user_id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        location: Optional[str] = None,
        connected: Optional[bool] = None,
        account_type: Optional[AccountTypeEnum] = None,
    ):
        query: Dict[str, Any] = InfluencerRepository.__construct_filters_query(
            user_id=user_id,
            name=name,
            email=email,
            platforms=platforms,
            location=location,
            connected=connected,
            account_type=account_type,
        )

        return await db["influencers"].count_documents(query)

    @staticmethod
    def __construct_filters_query(
        user_id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        location: Optional[str] = None,
        connected: Optional[bool] = None,
        account_type: Optional[AccountTypeEnum] = None,
        social_user_id: Optional[str] = None,
        social_username: Optional[str] = None,
        token: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> dict:
        query: Dict[str, Any] = {}

        if user_id is not None:
            query["user_id"] = user_id
        if name:
            query["name"] = {"$regex": name, "$options": "i"}
        if email:
            query["email"] = {"$regex": email, "$options": "i"}
        if platforms:
            query["$or"] = [{"social_platform": {"$in": platforms}}]
        if location:
            query["location"] = {"$regex": location, "$options": "i"}
        if connected is not None:
            query["connected"] = connected
        if account_type:
            query["account_type"] = account_type
        if social_user_id:
            query["social_user_id"] = social_user_id
        if social_username:
            query["social_username"] = social_username
        if token:
            query["token"] = token

        return query

    @staticmethod
    async def update_influencer(
        db: AsyncIOMotorDatabase, influencer: influencer_schema.InfluencerUpdate
    ) -> Any:
        db_influencer = influencer.dict(exclude_unset=True)
        db_influencer["updatedAt"] = DateHelper.utc_now_iso()

        result = await db["influencers"].update_one(
            {"influencer_id": influencer.influencer_id}, {"$set": db_influencer}
        )

        if result.matched_count == 0:
            return None

        return await InfluencerRepository.get_influencer_by_id(
            db, influencer.influencer_id
        )

    @staticmethod
    async def delete_influencer(db: AsyncIOMotorDatabase, influencer_id: str) -> Any:
        result = await db["influencers"].find_one_and_delete(
            {"influencer_id": influencer_id}
        )
        if not result:
            return UriResponse.delete_response("influencer", False)

        del result["_id"]
        return UriResponse.delete_response(
            "influencer", result is not None, data=result
        )

    @staticmethod
    async def delete_influencer_facebook(
        db: AsyncIOMotorDatabase, facebook_page_id: str
    ) -> Any:
        result = await db["influencers"].delete_many(
            {"facebook_page_id": facebook_page_id}
        )
        return UriResponse.delete_response("influencer", result.deleted_count > 0)

    @staticmethod
    async def create_or_update_influencer(
        db: AsyncIOMotorDatabase, influencer: influencer_schema.InfluencerCreate
    ) -> Dict[str, Any]:
        filter_criteria = {
            "user_id": influencer.user_id,
            "social_username": influencer.social_username,
            "social_platform": influencer.social_platform,
        }

        influencer_data = influencer.model_dump()  # Convert to dict
        influencer_data["updatedAt"] = DateHelper.utc_now_iso()

        existing_influencer = await db["influencers"].find_one(filter_criteria)

        if existing_influencer:
            influencer_token = existing_influencer.get("token")
            if influencer_token:
                if isinstance(influencer_token, dict):
                    influencer_data.get("token", {}).update(influencer_token)
                else:
                    influencer_data["token"] = influencer_token
            result = await db["influencers"].update_one(
                filter_criteria,
                {"$set": influencer_data},
            )
            return {
                "success": result.modified_count > 0,
                "data": influencer_data if result.modified_count else None,
            }
        else:
            influencer_data["influencer_id"] = str(ObjectId())
            influencer_data["createdAt"] = DateHelper.utc_now_iso()
            await db["influencers"].insert_one(influencer_data)
            return {"success": True, "data": influencer_data}

    @staticmethod
    async def create_multiple_influencers(
        db: AsyncIOMotorDatabase, influencers: List[influencer_schema.InfluencerCreate]
    ) -> Dict[str, Any]:
        inserted_influencers = []
        for influencer in influencers:
            result = await InfluencerRepository.create_or_update_influencer(
                db, influencer
            )
            if result.get("success"):
                inserted_influencers.append(result.get("data"))
            else:
                print(f"Failed to insert influencer: {influencer.social_username}")

        return UriResponse.create_response("influencers", inserted_influencers)

    @staticmethod
    async def get_social_user_token_by_username(
        db: AsyncIOMotorDatabase, username: str
    ) -> Optional[str]:
        influencer = await db["influencers"].find_one(
            {"social_username": username}, {"token": 1}
        )
        return influencer.get("token") if influencer else None

    @staticmethod
    async def get_social_user_token_social_id_and_user_id_by_influencer_id(
        db: AsyncIOMotorDatabase, influencer_id: str
    ) -> dict:
        influencer = await db["influencers"].find_one(
            {"influencer_id": influencer_id},
            {"token": 1, "social_user_id": 1, "user_id": 1},
        )
        return influencer

    @staticmethod
    async def get_influencer_specific_data_by_influencer_id(
        db: AsyncIOMotorDatabase, influencer_id: str, fields: List[str]
    ) -> dict:
        fields_dict = {key: 1 for key in fields}
        influencer = await db["influencers"].find_one(
            {"influencer_id": influencer_id}, fields_dict
        )
        return influencer

    @staticmethod
    async def get_influencer_by_username(db: AsyncIOMotorDatabase, username: str):
        return await db["influencers"].find_one({"social_username": username})
