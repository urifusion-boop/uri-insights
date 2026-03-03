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

        # Multi-form support: Allow multiple forms per user per type
        # No uniqueness constraint - users can create as many forms as needed

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

        # 🔍 LOG: Check what Pydantic dumped
        print(f"💾 [REPOSITORY UPDATE] Pydantic model_dump result:")
        print(f"   - enable_location_intelligence: {lead_form.get('enable_location_intelligence')}")
        print(f"   - location_zone_center_lat: {lead_form.get('location_zone_center_lat')}")
        print(f"   - location_zone_center_lng: {lead_form.get('location_zone_center_lng')}")
        print(f"   - location_zone_radius_km: {lead_form.get('location_zone_radius_km')}")
        print(f"   - location_zone_name: {lead_form.get('location_zone_name')}")
        print(f"   - min_trust_score: {lead_form.get('min_trust_score')}")

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
        """
        Delete a lead form with CASCADE DELETE.

        PRD Section 4.6: Deleting a form must delete:
        - The form itself
        - All associated snapshots
        - All associated leads
        - All associated spam items

        Args:
            db: Database connection
            lead_form_id: Lead form ID to delete

        Returns:
            UriResponse with deletion details
        """
        if not ObjectId.is_valid(lead_form_id):
            return UriResponse.custom_response("Invalid lead form ID")

        # Import repositories (avoid circular imports)
        from app.repository.LeadFormSnapshotRepository import LeadFormSnapshotRepository
        from app.repository.LeadRepository import LeadRepository
        from app.repository.SpamLeadRepository import SpamLeadRepository

        # Step 1: Get all snapshot IDs for this form
        snapshot_ids = await LeadFormSnapshotRepository.get_snapshot_ids_by_form_id(
            db, lead_form_id
        )

        # Step 2: Delete all leads associated with these snapshots
        leads_deleted = 0
        if snapshot_ids:
            leads_deleted = await LeadRepository.delete_leads_by_snapshot_ids(
                db, snapshot_ids
            )

        # Step 3: Delete all spam associated with these snapshots
        spam_deleted = 0
        if snapshot_ids:
            spam_deleted = await SpamLeadRepository.delete_spam_by_snapshot_ids(
                db, snapshot_ids
            )

        # Step 4: Delete all snapshots for this form
        snapshots_deleted = await LeadFormSnapshotRepository.delete_snapshots_by_form_id(
            db, lead_form_id
        )

        # Step 5: Delete the form itself
        result = await db[LeadFormRepository.COLLECTION_NAME].delete_one(
            {"lead_form_id": lead_form_id}
        )

        if result.deleted_count == 0:
            return UriResponse.custom_response("Lead form not found", 404)

        # Return success with details
        return UriResponse.custom_response(
            message=f"Lead form deleted successfully. "
            f"Also deleted: {snapshots_deleted} snapshots, {leads_deleted} leads, {spam_deleted} spam items.",
            error_code=200,
            success=True
        )

    # ========== Multi-Form Support Methods (PRD Section 4.1) ==========

    @staticmethod
    async def get_forms_by_user_and_type(
        db: AsyncIOMotorDatabase, user_id: str, form_type: LeadFormTypeEnum
    ) -> List[dict]:
        """
        Get all lead forms for a specific user and form type.
        Supports multiple forms per user per type (PRD 4.1).
        """
        cursor = db[LeadFormRepository.COLLECTION_NAME].find(
            {"user_id": user_id, "form_type": form_type.value}
        ).sort("created_date", -1)  # Most recent first

        results = await cursor.to_list(length=100)

        if not results:
            return []

        return [LeadForm(**form).dict() for form in results]

    @staticmethod
    async def set_default_form(
        db: AsyncIOMotorDatabase,
        user_id: str,
        form_type: LeadFormTypeEnum,
        lead_form_id: str,
    ):
        """
        Mark one form as default for a user and type.
        Unmarks all other forms of the same type.
        """
        # First, unmark all forms of this type for this user
        await db[LeadFormRepository.COLLECTION_NAME].update_many(
            {"user_id": user_id, "form_type": form_type.value},
            {"$set": {"is_default": False}},
        )

        # Then mark the specified form as default
        result = await db[LeadFormRepository.COLLECTION_NAME].update_one(
            {"lead_form_id": lead_form_id, "user_id": user_id},
            {"$set": {"is_default": True}},
        )

        if result.matched_count == 0:
            return UriResponse.custom_response("Lead form not found", 404)

        return UriResponse.success_response("Default form set successfully")

    @staticmethod
    async def get_default_form(
        db: AsyncIOMotorDatabase, user_id: str, form_type: LeadFormTypeEnum
    ):
        """
        Get the default form for a user and type.
        Falls back to most recent form if no default is set.
        """
        # Try to get default form
        result = await db[LeadFormRepository.COLLECTION_NAME].find_one(
            {"user_id": user_id, "form_type": form_type.value, "is_default": True}
        )

        # If no default, get most recent form
        if not result:
            result = await db[LeadFormRepository.COLLECTION_NAME].find_one(
                {"user_id": user_id, "form_type": form_type.value},
                sort=[("created_date", -1)],
            )

        if not result:
            return UriResponse.get_single_data_response("Lead form", None)

        return UriResponse.get_single_data_response(
            "Lead form", LeadForm(**result).dict()
        )

    @staticmethod
    async def migrate_existing_forms_to_multi_form_support(
        db: AsyncIOMotorDatabase,
    ):
        """
        One-time migration to add multi-form support fields to existing forms.
        - Sets is_default=True for all existing forms (backward compatibility)
        - Ensures existing single-form users see no change
        """
        result = await db[LeadFormRepository.COLLECTION_NAME].update_many(
            {"is_default": {"$exists": False}},  # Only update forms without is_default
            {"$set": {"is_default": True}},
        )

        print(f"✅ Migrated {result.modified_count} existing forms to multi-form support")
        return result.modified_count
