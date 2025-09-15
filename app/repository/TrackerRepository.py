from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.collection import Collection
from app import schemas
from bson import ObjectId
from app.domain.responses.uri_response import UriResponse


class TrackerRepository:
    @staticmethod
    async def create_tracker(
        db: AsyncIOMotorDatabase, tracker: schemas.TrackerCreate
    ) -> Dict[str, Any]:
        db_tracker = tracker.model_dump()
        db_tracker["tracker_id"] = str(ObjectId())

        await db["trackers"].insert_one(db_tracker)

        return UriResponse.create_response(
            "tracker",
            schemas.Tracker(**db_tracker, validate_assignment=False).model_dump(),
        )

    @staticmethod
    async def get_tracker_names_by_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        tracker_type: Optional[str] = "HASHTAG",
        limit: int = 10,
    ) -> List[str]:
        """
        Retrieves only the tracker names (keywords) for a given user to avoid heavy JSON responses.
        """
        query = {"user_id": user_id, "tracker_type": tracker_type}

        cursor = (
            db["trackers"]
            .find(query, {"keywords": 1})
            .sort("createdAt", -1)
            .limit(limit)
        )
        db_trackers = await cursor.to_list(length=limit)

        tracker_names = [
            tracker["keywords"][0]
            for tracker in db_trackers
            if "keywords" in tracker and tracker["keywords"]
        ]

        print("Tracker Names : ", tracker_names)
        return tracker_names

    @staticmethod
    async def get_tracker_by_id(db: AsyncIOMotorDatabase, tracker_id: str) -> Any:
        db_tracker = await db["trackers"].find_one({"tracker_id": tracker_id})

        if not db_tracker:
            return UriResponse.get_single_data_response("tracker", None)

        return UriResponse.get_single_data_response(
            "tracker",
            schemas.Tracker(**db_tracker, validate_assignment=False).model_dump(),
        )

    @staticmethod
    async def get_trackers_by_filter(
        db: AsyncIOMotorDatabase,
        user_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        tracker_type: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Any:
        query: Dict[str, Any] = TrackerRepository.__construct_trackers_filter_query(
            user_id=user_id,
            keywords=keywords,
            tracker_type=tracker_type,
            platforms=platforms,
            locations=locations,
        )
        cursor = (
            db["trackers"].find(query).sort("createdAt", -1).skip(skip).limit(limit)
        )
        db_trackers = await cursor.to_list(length=limit)

        trackers = [schemas.Tracker(**tracker).model_dump() for tracker in db_trackers]
        total_trackers = await db["trackers"].count_documents(query)

        return UriResponse.get_paged_data_response(
            "tracker", trackers, total_trackers, skip + 1, limit
        )

    @staticmethod
    async def get_trackers_count_by_filter(
        db: AsyncIOMotorDatabase,
        user_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        tracker_type: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
    ) -> int:
        query: Dict[str, Any] = TrackerRepository.__construct_trackers_filter_query(
            user_id=user_id,
            keywords=keywords,
            tracker_type=tracker_type,
            platforms=platforms,
            locations=locations,
        )
        total_trackers = await db["trackers"].count_documents(query)
        return total_trackers

    @staticmethod
    async def update_tracker(
        db: AsyncIOMotorDatabase, tracker: schemas.TrackerUpdate
    ) -> Any:
        db_tracker = tracker.model_dump(exclude_none=True)

        result = await db["trackers"].update_one(
            {"tracker_id": tracker.tracker_id}, {"$set": db_tracker}
        )

        if result.matched_count == 0:
            return None

        return await TrackerRepository.get_tracker_by_id(db, tracker.tracker_id)

    @staticmethod
    async def delete_tracker(db: AsyncIOMotorDatabase, tracker_id: str) -> Any:
        deleted_tracker = await db["trackers"].find_one_and_delete(
            {"tracker_id": tracker_id}
        )
        if not deleted_tracker:
            return UriResponse.delete_response("tracker", False)

        del deleted_tracker["_id"]
        return UriResponse.delete_response(
            "tracker", deleted_tracker is not None, data=deleted_tracker
        )

    @staticmethod
    async def get_alert_subscribed_trackers(
        db: AsyncIOMotorDatabase,
        skip: int = 0,
        limit: int = 10,
    ) -> Any:
        query = {"is_alert_subscribed": True}

        cursor = (
            db["trackers"].find(query).sort("createdAt", -1).skip(skip).limit(limit)
        )
        db_trackers = await cursor.to_list(length=limit)

        trackers = [schemas.Tracker(**tracker).model_dump() for tracker in db_trackers]
        total_trackers = await db["trackers"].count_documents(query)

        return UriResponse.get_paged_data_response(
            "tracker", trackers, total_trackers, skip + 1, limit
        )

    @staticmethod
    def __construct_trackers_filter_query(
        user_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        tracker_type: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
    ) -> Any:
        query: Dict[str, Any] = {}

        if user_id:
            query["user_id"] = user_id
        if keywords:
            query["keywords"] = {"$in": keywords}
        if tracker_type:
            query["tracker_type"] = tracker_type
        if platforms:
            query["platforms"] = {"$in": platforms}
        if locations:
            query["locations"] = {"$in": locations}

        return query
