from random import randint
import re
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from app.core.helpers.date_helper import DateHelper
from app.domain.enums.mention_enum import SentimentPriorityEnum
from app.domain.requests.mention_requests import AlertAnalyticsRequest
from app.domain.schemas.mention_schema import Mention, MentionCreate, MentionUpdate
from app.domain.responses.uri_response import UriResponse
from app.services.AIService import AIService
from app.services.GoogleService import GoogleService
from concurrent.futures import ThreadPoolExecutor
from app.services.NotificationService import NotificationService

executor = ThreadPoolExecutor()


class MentionRepository:
    @staticmethod
    async def create_mention(
        db: AsyncIOMotorDatabase, mention: MentionCreate
    ) -> Dict[str, Any]:
        mention_data = mention.dict()
        mention_data["mention_id"] = str(ObjectId())
        mention_data["created_at"] = datetime.utcnow().isoformat()
        mention_data["updated_at"] = datetime.utcnow().isoformat()

        sentiment_analysis = await AIService.analyze_sentiment(mention_data["comment"])
        mention_data["sentiment"] = sentiment_analysis.get("sentiment", "neutral")
        mention_data["sentiment_score"] = sentiment_analysis.get("score")

        await db["mentions"].insert_one(mention_data)

        if mention_data["sentiment_priority"] == SentimentPriorityEnum.HIGH.value:
            await NotificationService.notify_high_priority(mention.dict())

        return UriResponse.create_response("mention", Mention(**mention_data).dict())

    @staticmethod
    async def update_mention(
        db: AsyncIOMotorDatabase, mention_id: str, updates: MentionUpdate
    ) -> Dict[str, Any]:
        updates_data = updates.dict(exclude_unset=True)
        updates_data["updated_at"] = datetime.utcnow().isoformat()

        result = await db["mentions"].update_one(
            {"mention_id": mention_id}, {"$set": updates_data}
        )
        if result.matched_count == 0:
            return UriResponse.get_single_data_response(
                "mention", None, "Mention not found."
            )

        updated_mention = await db["mentions"].find_one({"mention_id": mention_id})
        return UriResponse.update_response("mention", Mention(**updated_mention).dict())

    @staticmethod
    async def get_mention_by_id(
        db: AsyncIOMotorDatabase, mention_id: str
    ) -> Dict[str, Any]:
        mention = await db["mentions"].find_one({"mention_id": mention_id})
        return UriResponse.get_single_data_response(
            "mention", Mention(**mention).dict() if mention else None
        )

    @staticmethod
    async def get_mentions_by_filters(
        db: AsyncIOMotorDatabase,
        user_id: Optional[str] = None,
        deleted: Optional[bool] = None,
        unread: Optional[bool] = None,
        read: Optional[bool] = None,
        starred: Optional[bool] = None,
        processed: Optional[bool] = None,
        skip: int = 0,
        limit: int = 10,
    ):
        query: Dict[str, Any] = {}
        if user_id is not None:
            query["user_id"] = user_id
        if deleted is not None:
            query["deleted"] = deleted
        if unread is True:
            query["is_read"] = False
        if read is True:
            query["is_read"] = True
        if starred is not None:
            query["starred"] = starred
        if processed is not None:
            query["processed"] = processed

        total_mentions = await db["mentions"].count_documents(query)
        total_unread = await db["mentions"].count_documents({**query, "is_read": False})
        total_with_deleted = await db["mentions"].count_documents({"user_id": user_id})
        total = await db["mentions"].count_documents(
            {"user_id": user_id, "deleted": False}
        )

        cursor = (
            db["mentions"].find(query).sort("created_at", -1).skip(skip).limit(limit)
        )
        mentions = await cursor.to_list(length=limit)

        mentions_list = [Mention(**mention).dict() for mention in mentions]
        return UriResponse.get_paged_data_response(
            "mentions",
            mentions_list,
            total,
            skip + 1,
            total_mentions,
            {
                "total_unread": total_unread,
                "total_with_deleted": total_with_deleted,
            },
        )

    @staticmethod
    async def mark_as_read(db: AsyncIOMotorDatabase, mention_id: str) -> Dict[str, Any]:
        result = await db["mentions"].update_one(
            {"mention_id": mention_id},
            {"$set": {"is_read": True, "updated_at": datetime.utcnow().isoformat()}},
        )
        if result.matched_count == 0:
            return UriResponse.get_single_data_response(
                "mention", None, "Mention not found."
            )

        mention = await db["mentions"].find_one({"mention_id": mention_id})
        return UriResponse.update_response("mention", Mention(**mention).dict())

    @staticmethod
    async def mark_as_starred(
        db: AsyncIOMotorDatabase, mention_id: str, starred: bool
    ) -> Dict[str, Any]:
        result = await db["mentions"].update_one(
            {"mention_id": mention_id},
            {"$set": {"starred": starred, "updated_at": datetime.utcnow().isoformat()}},
        )
        if result.matched_count == 0:
            return UriResponse.get_single_data_response(
                "mention", None, "Mention not found."
            )

        mention = await db["mentions"].find_one({"mention_id": mention_id})
        return UriResponse.update_response("mention", Mention(**mention).dict())

    @staticmethod
    async def delete_mention(
        db: AsyncIOMotorDatabase, mention_id: str
    ) -> Dict[str, Any]:
        result = await db["mentions"].update_one(
            {"mention_id": mention_id},
            {"$set": {"deleted": True, "updated_at": datetime.utcnow().isoformat()}},
        )
        if result.matched_count == 0:
            return UriResponse.delete_response("mention", False, "Mention not found.")
        return UriResponse.delete_response("mention", True)

    @staticmethod
    async def multiple_create_mentions(
        db: AsyncIOMotorDatabase, mentions: List[MentionCreate]
    ) -> Dict[str, Any]:
        mention_data_list = []
        MAX_NOTIFICATIONS = 2

        for mention in mentions:
            mention_data = mention.dict()
            mention_data["mention_id"] = str(ObjectId())
            mention_data["created_at"] = datetime.utcnow().isoformat()
            mention_data["updated_at"] = datetime.utcnow().isoformat()
            mention_data_list.append(mention_data)

        for i in range(min(MAX_NOTIFICATIONS, len(mention_data_list))):
            if (
                mention_data_list[i].get("sentiment_priority")
                == SentimentPriorityEnum.HIGH.value
            ):
                await NotificationService.notify_high_priority(mention_data_list[i])

        await db["mentions"].insert_many(mention_data_list)

        created_mentions = [Mention(**mention).dict() for mention in mention_data_list]
        return UriResponse.create_multiple_response("mention", created_mentions)

    @staticmethod
    async def fetch_alerts_by_date_range(
        db: AsyncIOMotorDatabase, request: AlertAnalyticsRequest
    ):
        start_date = end_date = None
        if request.date_filter:
            start_date, end_date = DateHelper.get_date_range(request.date_filter)

        query: dict = {}
        if request.user_id:
            query["user_id"] = request.user_id
        if start_date and end_date:
            query["created_at"] = {
                "$gte": start_date,
                "$lte": end_date,
            }

        cursor = db["mentions"].find(query).sort("created_at", -1)
        alerts = await cursor.to_list(length=1000)

        return UriResponse.get_list_data_response("alert", alerts)

    @staticmethod
    async def clean_comment(comment: str) -> str:
        return re.sub(
            r"\b\d+\s+(?:minutes|hours|days|weeks|months|years)\s+ago\b",
            "",
            comment,
            flags=re.IGNORECASE,
        ).strip()
