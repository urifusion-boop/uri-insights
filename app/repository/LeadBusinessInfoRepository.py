import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta
from app.core.helpers.date_helper import DateHelper
from app.domain.enums.lead_enum import LeadsProcessedStatus
from app.domain.responses.uri_response import UriResponse
from app.domain.schemas.leadbusinessinfo_schema import (
    LeadBusinessInfo,
    LeadBusinessInfoCreate,
    LeadBusinessInfoUpdate,
    LeadSourceSettings,
    LeadSourceSettingsCreate,
)
from app.core.config import settings


class LeadBusinessInfoRepository:
    @staticmethod
    async def create(
        db: AsyncIOMotorDatabase, lead_business_info: LeadBusinessInfoCreate
    ):
        lead_business_info_data = lead_business_info.dict()

        existing_instance = await db["lead_business_info"].find_one(
            {"user_id": lead_business_info_data.get("user_id")}
        )

        if existing_instance:
            return UriResponse.conflict_response("lead business info", "already exists")

        lead_business_info_data["lead_business_info_id"] = str(ObjectId())
        lead_business_info_data["created_date"] = DateHelper.utc_now_iso()
        lead_business_info_data["last_updated"] = DateHelper.utc_now_iso()

        await db["lead_business_info"].insert_one(lead_business_info_data)

        return UriResponse.create_response(
            "lead business info", LeadBusinessInfo(**lead_business_info_data).dict()
        )

    @staticmethod
    async def update(
        db: AsyncIOMotorDatabase,
        lead_business_info_id: str,
        updates: LeadBusinessInfoUpdate,
    ):
        updates_data = updates.dict(exclude_unset=True)
        updates_data["last_updated"] = DateHelper.utc_now_iso()

        result = await db["lead_business_info"].find_one_and_update(
            {"lead_business_info_id": lead_business_info_id},
            {"$set": updates_data},
            return_document=True,
        )

        if not result:
            return UriResponse.get_single_data_response("lead business info", None)

        return UriResponse.update_response(
            "lead business info", LeadBusinessInfo(**result).dict()
        )

    @staticmethod
    async def get_lead_business_info_by_id(
        db: AsyncIOMotorDatabase, lead_business_info_id: str
    ) -> Dict[str, Any]:
        lead_business_info = await db["lead_business_info"].find_one(
            {"lead_business_info_id": lead_business_info_id}
        )

        return UriResponse.get_single_data_response(
            "lead business info",
            (
                LeadBusinessInfo(**lead_business_info).dict()
                if lead_business_info
                else None
            ),
        )

    @staticmethod
    async def get_lead_business_info_by_filters(
        db: AsyncIOMotorDatabase,
        user_id: str,
        business_name: Optional[str] = None,
        business_website: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        query: Dict[str, Any] = {}
        if user_id is not None:
            query["user_id"] = user_id
        elif business_name is not None:
            query["business_name"] = business_name
        elif business_website is not None:
            query["business_website"] = business_website

        total_lead_business_infos = await db["lead_business_info"].count_documents(
            query
        )
        lead_business_infos = (
            await db["lead_business_info"]
            .find(query)
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        lead_business_info_list = [
            LeadBusinessInfo(**lead_business_info).dict()
            for lead_business_info in lead_business_infos
        ]

        return UriResponse.get_paged_data_response(
            "leads", lead_business_info_list, total_lead_business_infos, skip + 1, limit
        )

    @staticmethod
    async def delete_leads_business_info(
        db: AsyncIOMotorDatabase, lead_business_info_id: str
    ) -> Dict[str, Any]:
        result = await db["lead_business_info"].delete_one(
            {"lead_business_info_id": lead_business_info_id}
        )

        if result.deleted_count == 0:
            return UriResponse.delete_response(
                "lead business info", False, "Lead business info not found."
            )

        return UriResponse.delete_response("lead business info", True)

    @staticmethod
    async def get_lead_business_info_for_tracking(
        db: AsyncIOMotorDatabase,
        skip: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        lead_business_infos = (
            await db["lead_business_info"]
            .find({})
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )

        lead_business_info_list = [
            LeadBusinessInfo(**lead_business_info).dict()
            for lead_business_info in lead_business_infos
        ]

        return UriResponse.get_paged_data_response(
            "leads", lead_business_info_list, 0, skip + 1, limit
        )

    @staticmethod
    async def create_settings(db: AsyncIOMotorDatabase, lead_business_info_id: str):
        lead_source_settings_create = LeadSourceSettingsCreate(
            lead_business_info_id=lead_business_info_id
        )
        lead_business_info = await db["lead_business_info"].find_one_and_update(
            {"lead_business_info_id": lead_business_info_id},
            {"$set": {"settings": lead_source_settings_create.dict()}},
        )
        if not lead_business_info:
            return UriResponse.get_single_data_response("lead business info", None)
        return UriResponse.create_response(
            "lead business info", LeadBusinessInfo(**lead_business_info).dict()
        )

    @staticmethod
    async def fetch_user_business_info_in_batches(
        db: AsyncIOMotorDatabase, batch_size: int = 10
    ) -> AsyncGenerator[List[dict], None]:
        cursor = db["lead_business_info"].find({})

        while True:
            batch = []
            try:
                for _ in range(batch_size):
                    doc = await cursor.next()
                    batch.append(LeadBusinessInfo(**doc).dict(exclude_none=True))
            except StopAsyncIteration:
                pass

            if not batch:
                break
            yield batch
            await asyncio.sleep(15)
        await cursor.close()

    @staticmethod
    async def update_user_next_generation_time(
        db: AsyncIOMotorDatabase, user_id: Optional[str]
    ):
        if user_id:
            business_info = (
                (
                    await LeadBusinessInfoRepository.get_lead_business_info_by_filters(
                        db, user_id
                    )
                )
                .get("responseData", {})
                .get("data", [])[0]
            )

            updated_lead_business_info = await LeadBusinessInfoRepository.update(
                db,
                business_info.get("lead_business_info_id"),
                LeadBusinessInfoUpdate(
                    next_generation_date=datetime.utcnow()
                    + timedelta(hours=settings.LEAD_GENERATION_INTERVAL)
                ),
            )
            return updated_lead_business_info

    @staticmethod
    async def update_user_lead_settings(
        db: AsyncIOMotorDatabase,
        user_id: Optional[str],
        lead_processed_status: LeadsProcessedStatus = LeadsProcessedStatus.COMPLETED,
    ):
        if user_id:
            response = (
                await LeadBusinessInfoRepository.get_lead_business_info_by_filters(
                    db, user_id
                )
            )

            if response.get("status"):
                business_info = response.get("responseData", {}).get("data", [])[0]

                updated_lead_business_info = await LeadBusinessInfoRepository.update(
                    db,
                    business_info.get("lead_business_info_id"),
                    LeadBusinessInfoUpdate(
                        settings=LeadSourceSettings(
                            last_scraped_date=datetime.utcnow(),
                            last_scraped_status=lead_processed_status,
                        )
                    ),
                )

                return updated_lead_business_info
