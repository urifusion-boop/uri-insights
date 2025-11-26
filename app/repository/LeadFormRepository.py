import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.config import settings
from app.core.helpers.date_helper import DateHelper
from app.domain.enums.lead_enum import LeadsProcessedStatus
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.domain.responses.uri_response import UriResponse
from app.domain.schemas.leadform_schema import (
    LeadForm,
    LeadFormCreate,
    LeadFormUpdateBase,
)
from app.domain.schemas.leadformsnapshot_schema import LeadFormSnapshot
from app.repository.LeadFormSnapshotRepository import LeadFormSnapshotRepository


class LeadFormRepository:
    COLLECTION_NAME = "lead_form"

    @staticmethod
    async def add_auto_generate_field_to_all_lead_forms(
        db: AsyncIOMotorDatabase, auto_generate: bool = False
    ):
        """
        Add the auto_generate field to all lead forms.
        """
        await db[LeadFormRepository.COLLECTION_NAME].update_many(
            {}, {"$set": {"auto_generate": auto_generate}}
        )

    @staticmethod
    async def create(db: AsyncIOMotorDatabase, lead_form: LeadFormCreate):
        lead_form_data = lead_form.dict()
        existing_instance = await db[LeadFormRepository.COLLECTION_NAME].find_one(
            {
                "user_id": lead_form_data.get("user_id"),
                "form_type": lead_form_data.get("form_type"),
            }
        )

        if existing_instance:
            return UriResponse.conflict_response("lead form", "already exists")

        await db[LeadFormRepository.COLLECTION_NAME].insert_one(lead_form_data)

        if lead_form.add_to_history:
            create_snapshot_response = await LeadFormSnapshotRepository.create(
                db, LeadFormSnapshot(**lead_form_data)
            )

            if not create_snapshot_response.get("status"):
                return UriResponse.custom_response(
                    "Lead form snapshot not created successfully."
                )

        return UriResponse.create_response(
            "lead form created", LeadForm(**lead_form_data).model_dump()
        )

    @staticmethod
    async def get_by_id(db: AsyncIOMotorDatabase, lead_form_id: str):
        if not ObjectId.is_valid(lead_form_id):
            return UriResponse.custom_response("Invalid lead form ID")

        result = await db[LeadFormRepository.COLLECTION_NAME].find_one(
            {"lead_form_id": lead_form_id}
        )

        if not result:
            return UriResponse.get_single_data_response("Lead form", None)

        return UriResponse.get_single_data_response(
            "Lead form", LeadForm(**result).dict()
        )

    @staticmethod
    async def get_by_filters(db: AsyncIOMotorDatabase, filters: dict):
        cursor = db[LeadFormRepository.COLLECTION_NAME].find(filters)
        results = await cursor.to_list(length=100)
        if not results:
            return UriResponse.get_list_data_response("Lead form", [])

        lead_forms = [LeadForm(**lead_form).model_dump() for lead_form in results]

        return UriResponse.get_list_data_response("Lead form", lead_forms)

    @staticmethod
    async def update(
        db: AsyncIOMotorDatabase, data: LeadFormUpdateBase, lead_form_id: str
    ):
        lead_form = data.model_dump(exclude_unset=True)
        lead_form["last_updated"] = DateHelper.utc_now_iso()

        existing_form = (await LeadFormRepository.get_by_id(db, lead_form_id)).get(
            "responseData"
        )

        if not existing_form:
            return UriResponse.custom_response("Lead form not found.", 404)

        lead_form_type = existing_form.get("form_type")

        valid_form_types = [
            LeadFormTypeEnum.PERSON.value,
            LeadFormTypeEnum.ORGANIZATION.value,
            LeadFormTypeEnum.CONVERSATIONAL.value,
            LeadFormTypeEnum.BUSINESS.value,
        ]

        if lead_form_type not in valid_form_types:
            return UriResponse.custom_response(
                f"Unsupported lead form type: {lead_form_type}", 400
            )

        result = await db[LeadFormRepository.COLLECTION_NAME].update_one(
            {"lead_form_id": lead_form_id}, {"$set": lead_form}
        )

        if result.matched_count == 0:
            return None

        updated_form_response = await LeadFormRepository.get_by_id(db, lead_form_id)

        if updated_form_response.get("status"):
            if data.add_to_history:
                await LeadFormSnapshotRepository.create(
                    db, LeadFormSnapshot(**updated_form_response.get("responseData"))
                )
        return updated_form_response

    @staticmethod
    async def update_user_next_generation_time(
        db: AsyncIOMotorDatabase, user_id: Optional[str]
    ):
        if not user_id:
            return

        filters = {
            "user_id": user_id,
            "form_type": LeadFormTypeEnum.BUSINESS.value,
        }

        existing_form = (await LeadFormRepository.get_by_filters(db, filters)).get(
            "responseData", []
        )

        if not existing_form:
            return

        lead_form = existing_form[0]
        lead_form_id = lead_form.get("lead_form_id")

        updated_data = {
            "next_generation_date": datetime.utcnow()
            + timedelta(hours=settings.LEAD_GENERATION_INTERVAL)
        }

        await db[LeadFormRepository.COLLECTION_NAME].update_one(
            {"lead_form_id": lead_form_id}, {"$set": updated_data}
        )

        return await LeadFormRepository.get_by_id(db, lead_form_id)

    @staticmethod
    async def update_user_lead_settings(
        db: AsyncIOMotorDatabase,
        user_id: Optional[str],
        lead_processed_status: LeadsProcessedStatus = LeadsProcessedStatus.COMPLETED,
    ):
        if not user_id:
            return

        filters = {
            "user_id": user_id,
            "form_type": LeadFormTypeEnum.BUSINESS.value,
        }

        existing_form = (await LeadFormRepository.get_by_filters(db, filters)).get(
            "responseData", []
        )

        if not existing_form:
            return

        lead_form = existing_form[0]
        lead_form_id = lead_form.get("lead_form_id")

        settings = {
            "last_scraped_date": datetime.utcnow(),
            "last_scraped_status": lead_processed_status,
        }

        await db[LeadFormRepository.COLLECTION_NAME].update_one(
            {"lead_form_id": lead_form_id}, {"$set": {"settings": settings}}
        )

        return await LeadFormRepository.get_by_id(db, lead_form_id)

    @staticmethod
    async def fetch_lead_forms_in_batches(
        db: AsyncIOMotorDatabase, batch_size: int = 10, filter: Optional[dict] = None
    ) -> AsyncGenerator[List[dict], None]:
        cursor = db[LeadFormRepository.COLLECTION_NAME].find(filter)

        while True:
            batch = []
            try:
                for _ in range(batch_size):
                    doc = await cursor.next()
                    batch.append(LeadForm(**doc).dict(exclude_none=True))
            except StopAsyncIteration:
                pass

            if not batch:
                break

            yield batch
            await asyncio.sleep(1)

        await cursor.close()

    @staticmethod
    async def change_conversational_lead_forms_to_business_lead_forms(
        db: AsyncIOMotorDatabase,
    ):
        async for batch in LeadFormRepository.fetch_lead_forms_in_batches(
            db, filter={"form_type": LeadFormTypeEnum.CONVERSATIONAL.value}
        ):
            update_tasks = [
                LeadFormRepository.update(
                    db,
                    lead_form_id=lead_form["lead_form_id"],
                    data=LeadFormUpdateBase(form_type=LeadFormTypeEnum.BUSINESS.value),
                )
                for lead_form in batch
            ]

            await asyncio.gather(*update_tasks, return_exceptions=True)

    @staticmethod
    async def delete(db: AsyncIOMotorDatabase, lead_form_id: str):
        if not ObjectId.is_valid(lead_form_id):
            return UriResponse.custom_response("Invalid lead form ID")

        result = await db[LeadFormRepository.COLLECTION_NAME].delete_one(
            {"lead_form_id": lead_form_id}
        )

        return UriResponse.delete_response("Lead form", result.deleted_count > 0)
