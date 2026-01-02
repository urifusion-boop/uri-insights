from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import pymongo
import pymongo.errors

from app.domain.schemas.leadformsnapshot_schema import (
    LeadFormSnapshot,
)
from app.domain.responses.uri_response import UriResponse


class LeadFormSnapshotRepository:
    COLLECTION_NAME = "lead_form_snapshots"

    @staticmethod
    async def setup_indexes(db: AsyncIOMotorDatabase):
        try:
            print("⚙️ Setting up indexes for 'Lead Form Snapshots' collection...")
            await db[LeadFormSnapshotRepository.COLLECTION_NAME].create_index(
                [
                    ("form_title", 1),
                    ("form_type", 1),
                    ("user_id", 1),
                    ("person_titles", 1),
                    ("q_keywords", 1),
                    ("q_organization_name", 1),
                    ("q_organization_keyword_tags", 1),
                ],
                unique=True,
                sparse=True,
                name="LeadFormSnapshot-Index",
            )
            print("✅ Indexes created successfully.")
        except Exception as e:
            print("❌ Failed to set up indexes: ", e)

    @staticmethod
    async def create(
        db: AsyncIOMotorDatabase,
        snapshot: LeadFormSnapshot,
    ):
        snapshot_data = snapshot.dict()

        snapshot_data["created_date"] = datetime.utcnow()
        snapshot_data["last_updated"] = datetime.utcnow()

        try:
            await db[LeadFormSnapshotRepository.COLLECTION_NAME].insert_one(
                snapshot_data
            )
        except pymongo.errors.DuplicateKeyError:
            print("A duplicate of this snapshot already exists.")

        return UriResponse.create_response("lead form snapshot created", snapshot_data)

    @staticmethod
    async def get_by_id(db: AsyncIOMotorDatabase, lead_form_snapshot_id: str):
        if not ObjectId.is_valid(lead_form_snapshot_id):
            return UriResponse.custom_response("Invalid snapshot ID")

        result = await db[LeadFormSnapshotRepository.COLLECTION_NAME].find_one(
            {"lead_form_snapshot_id": lead_form_snapshot_id}
        )

        if not result:
            return UriResponse.get_single_data_response("Lead form snapshot", None)

        return UriResponse.get_single_data_response(
            "Lead form snapshot", LeadFormSnapshot(**result).dict()
        )

    @staticmethod
    async def get_all_by_lead_form_id(
        db: AsyncIOMotorDatabase, lead_form_id: str, skip: int = 0, limit: int = 10
    ):
        query = {"lead_form_id": lead_form_id}
        results = (
            await db[LeadFormSnapshotRepository.COLLECTION_NAME]
            .find(query)
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )

        total = await db[LeadFormSnapshotRepository.COLLECTION_NAME].count_documents(
            query
        )

        snapshots = [LeadFormSnapshot(**snap).dict() for snap in results]

        return UriResponse.get_paged_data_response(
            "Lead form snapshot", snapshots, total, skip + 1, limit
        )

    @staticmethod
    async def get_latest_snapshot(db: AsyncIOMotorDatabase, filters: dict):
        result = (
            await db[LeadFormSnapshotRepository.COLLECTION_NAME]
            .find(filters)
            .sort("created_date", -1)
            .skip(0)
            .limit(4)
            .to_list(length=4)
        )

        if result:
            lead_form_snapshot = LeadFormSnapshot(**result[0])

            return UriResponse.get_single_data_response(
                "Lead form snapshot", lead_form_snapshot
            )
        return UriResponse.get_single_data_response("Lead form snapshot", None)

    @staticmethod
    async def get_by_filters(
        db: AsyncIOMotorDatabase, filters: dict, skip: int = 0, limit: int = 10
    ):
        results = (
            await db[LeadFormSnapshotRepository.COLLECTION_NAME]
            .find(filters)
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )

        total = await db[LeadFormSnapshotRepository.COLLECTION_NAME].count_documents(
            filters
        )

        snapshots = [LeadFormSnapshot(**snap).dict() for snap in results]

        return UriResponse.get_paged_data_response(
            "Lead form snapshot", snapshots, total, skip + 1, limit
        )

    @staticmethod
    async def delete(
        db: AsyncIOMotorDatabase,
        lead_form_snapshot_id: str,
    ):
        if not ObjectId.is_valid(lead_form_snapshot_id):
            return UriResponse.custom_response("Invalid snapshot ID")

        result = await db[LeadFormSnapshotRepository.COLLECTION_NAME].delete_one(
            {"lead_form_snapshot_id": lead_form_snapshot_id}
        )

        return UriResponse.delete_response(
            "Lead form snapshot", result.deleted_count > 0
        )

    @staticmethod
    async def get_snapshot_ids_by_form_id(
        db: AsyncIOMotorDatabase,
        lead_form_id: str
    ) -> list:
        """
        Get all snapshot IDs for a given lead form.

        PRD Section 4.6: Needed for cascade delete

        Args:
            db: Database connection
            lead_form_id: Lead form ID

        Returns:
            List of lead_form_snapshot_id values
        """
        cursor = db[LeadFormSnapshotRepository.COLLECTION_NAME].find(
            {"lead_form_id": lead_form_id},
            {"lead_form_snapshot_id": 1, "_id": 0}
        )

        snapshots = await cursor.to_list(length=None)
        return [snap["lead_form_snapshot_id"] for snap in snapshots if "lead_form_snapshot_id" in snap]

    @staticmethod
    async def delete_snapshots_by_form_id(
        db: AsyncIOMotorDatabase,
        lead_form_id: str
    ) -> int:
        """
        Delete all snapshots for a given lead form.

        PRD Section 4.6: Deleting a form deletes associated snapshots

        Args:
            db: Database connection
            lead_form_id: Lead form ID

        Returns:
            Number of snapshots deleted
        """
        result = await db[LeadFormSnapshotRepository.COLLECTION_NAME].delete_many(
            {"lead_form_id": lead_form_id}
        )

        return result.deleted_count
