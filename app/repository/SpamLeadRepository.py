"""
Spam Lead Repository - Database operations for spam collection

NEW REPOSITORY - Does not modify existing LeadRepository
Handles all CRUD operations for spam leads (analyzed but unqualified items)

PRD Reference: Lead Gen Enhancement PRD - Spam Visibility Feature
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.schemas.spam_lead_schema import SpamLeadCreate, SpamLead
from app.domain.responses.uri_response import UriResponse


class SpamLeadRepository:
    """
    Repository for spam leads (unqualified but analyzed items)

    PRD Section 3.4: Spam Tab/Section Requirements
    PRD Section 4.7: Spam scoped per lead form
    """

    COLLECTION_NAME = "spam"  # PRD uses "spam" terminology

    @staticmethod
    async def save_spam_lead(
        db: AsyncIOMotorDatabase,
        spam_lead: SpamLeadCreate
    ) -> Dict[str, Any]:
        """
        Save a single spam lead to database

        Args:
            db: Database connection
            spam_lead: SpamLeadCreate object

        Returns:
            Saved spam lead document
        """
        collection = db[SpamLeadRepository.COLLECTION_NAME]
        spam_dict = spam_lead.dict()

        # Insert into spam collection
        result = await collection.insert_one(spam_dict)

        # Return inserted document
        spam_dict["_id"] = str(result.inserted_id)
        return spam_dict

    @staticmethod
    async def save_spam_leads_batch(
        db: AsyncIOMotorDatabase,
        spam_leads: List[SpamLeadCreate]
    ) -> List[Dict[str, Any]]:
        """
        Bulk insert spam leads

        Used when saving multiple filtered items from a single search

        Args:
            db: Database connection
            spam_leads: List of SpamLeadCreate objects

        Returns:
            List of inserted spam lead documents
        """
        if not spam_leads:
            return []

        collection = db[SpamLeadRepository.COLLECTION_NAME]
        spam_dicts = [spam.dict() for spam in spam_leads]

        # Bulk insert
        result = await collection.insert_many(spam_dicts)

        # Add IDs to documents
        for i, inserted_id in enumerate(result.inserted_ids):
            spam_dicts[i]["_id"] = str(inserted_id)

        return spam_dicts

    @staticmethod
    async def get_spam_leads_by_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        lead_form_snapshot_id: Optional[str] = None,
        filter_stage: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get spam leads for a user with pagination

        PRD Section 4.7: Spam scoped per form - must filter by lead_form_snapshot_id

        Args:
            db: Database connection
            user_id: User ID
            lead_form_snapshot_id: Filter by specific lead form (PRD 4.7)
            filter_stage: Filter by stage ("job_board_ai", "intent_analysis", etc.)
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (spam_leads list, total count)
        """
        collection = db[SpamLeadRepository.COLLECTION_NAME]

        # Build query
        query = {"user_id": user_id}

        # PRD Section 4.7: Scope by lead form
        if lead_form_snapshot_id:
            query["lead_form_snapshot_id"] = lead_form_snapshot_id

        # Optional filter by stage
        if filter_stage:
            query["filter_stage"] = filter_stage

        # Calculate pagination
        skip = (page - 1) * page_size

        # Get total count
        total = await collection.count_documents(query)

        # Get paginated results (sorted by newest first)
        cursor = collection.find(query).sort("spam_timestamp", -1).skip(skip).limit(page_size)
        spam_leads = await cursor.to_list(length=page_size)

        # Convert ObjectId to string
        for spam in spam_leads:
            if "_id" in spam:
                spam["_id"] = str(spam["_id"])

        return spam_leads, total

    @staticmethod
    async def get_spam_lead_by_id(
        db: AsyncIOMotorDatabase,
        spam_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single spam lead by ID

        Args:
            db: Database connection
            spam_id: Spam lead ID

        Returns:
            Spam lead document or None if not found
        """
        collection = db[SpamLeadRepository.COLLECTION_NAME]

        spam_lead = await collection.find_one({"spam_id": spam_id})

        if spam_lead:
            spam_lead["_id"] = str(spam_lead["_id"])

        return spam_lead

    @staticmethod
    async def promote_spam_to_lead(
        db: AsyncIOMotorDatabase,
        spam_id: str
    ) -> bool:
        """
        Mark spam lead as promoted to qualified leads

        PRD Section 3.5: "Add to Leads" action
        Does NOT delete from spam, just marks as promoted for tracking

        Args:
            db: Database connection
            spam_id: Spam lead ID

        Returns:
            True if updated successfully
        """
        collection = db[SpamLeadRepository.COLLECTION_NAME]

        result = await collection.update_one(
            {"spam_id": spam_id},
            {
                "$set": {
                    "promoted_to_leads": True,
                    "promoted_at": datetime.utcnow(),
                    "user_reviewed": True
                }
            }
        )

        return result.modified_count > 0

    @staticmethod
    async def move_lead_to_spam(
        db: AsyncIOMotorDatabase,
        lead_data: Dict[str, Any],
        spam_reason: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Move a qualified lead to spam (reverse action)

        PRD Section 3.6: Lead → Spam
        Creates spam entry from existing lead data

        Args:
            db: Database connection
            lead_data: Complete lead document
            spam_reason: Why user is marking as spam
            user_id: User performing the action

        Returns:
            Created spam lead document
        """
        from app.domain.schemas.spam_lead_schema import SpamLeadCreate
        from app.domain.enums.spam_enum import SpamReasonEnum, SpamFilterStageEnum

        collection = db[SpamLeadRepository.COLLECTION_NAME]

        # Create spam lead from existing lead
        spam_lead = SpamLeadCreate(
            user_id=user_id,
            original_lead_data=lead_data,
            spam_reason=spam_reason,
            spam_reason_detail="Manually moved from qualified leads by user",
            filter_stage=SpamFilterStageEnum.INTENT_ANALYSIS.value,  # Default
            lead_source=lead_data.get("lead_source", "Unknown"),
            search_keyword=lead_data.get("keywords", ["Unknown"])[0] if lead_data.get("keywords") else "Unknown",
            lead_form_snapshot_id=lead_data.get("lead_form_snapshot_id", ""),

            # Display fields
            display_title=lead_data.get("job_title_field") or lead_data.get("mention", "")[:100],
            display_company=lead_data.get("hiring_company") or lead_data.get("company_name"),
            display_username=lead_data.get("username") or lead_data.get("hiring_company"),
            display_link=lead_data.get("job_posting_url") or lead_data.get("lead_link"),
            display_source=lead_data.get("job_source") or lead_data.get("lead_source"),

            # Mark as moved from leads
            moved_from_leads=True,
            moved_from_leads_at=datetime.utcnow(),
            user_reviewed=True
        )

        spam_dict = spam_lead.dict()
        result = await collection.insert_one(spam_dict)
        spam_dict["_id"] = str(result.inserted_id)

        return spam_dict

    @staticmethod
    async def delete_spam_by_form(
        db: AsyncIOMotorDatabase,
        lead_form_snapshot_id: str
    ) -> int:
        """
        Delete all spam leads for a specific lead form snapshot

        PRD Section 4.6: Deleting a form deletes associated spam items

        Args:
            db: Database connection
            lead_form_snapshot_id: Single snapshot ID

        Returns:
            Number of spam leads deleted
        """
        collection = db[SpamLeadRepository.COLLECTION_NAME]

        result = await collection.delete_many({
            "lead_form_snapshot_id": lead_form_snapshot_id
        })

        return result.deleted_count

    @staticmethod
    async def delete_spam_by_snapshot_ids(
        db: AsyncIOMotorDatabase,
        snapshot_ids: List[str]
    ) -> int:
        """
        Delete all spam leads for multiple form snapshots

        PRD Section 4.6: Deleting a form deletes associated spam items

        Args:
            db: Database connection
            snapshot_ids: List of lead_form_snapshot_id values

        Returns:
            Number of spam leads deleted
        """
        if not snapshot_ids:
            return 0

        collection = db[SpamLeadRepository.COLLECTION_NAME]

        result = await collection.delete_many({
            "lead_form_snapshot_id": {"$in": snapshot_ids}
        })

        return result.deleted_count

    @staticmethod
    async def update_spam_notes(
        db: AsyncIOMotorDatabase,
        spam_id: str,
        user_notes: str
    ) -> bool:
        """
        Add user notes to spam lead

        Allows users to document why they reviewed/promoted/dismissed an item

        Args:
            db: Database connection
            spam_id: Spam lead ID
            user_notes: User's notes

        Returns:
            True if updated successfully
        """
        collection = db[SpamLeadRepository.COLLECTION_NAME]

        result = await collection.update_one(
            {"spam_id": spam_id},
            {
                "$set": {
                    "user_notes": user_notes,
                    "user_reviewed": True
                }
            }
        )

        return result.modified_count > 0

    @staticmethod
    async def mark_as_reviewed(
        db: AsyncIOMotorDatabase,
        spam_id: str
    ) -> bool:
        """
        Mark spam lead as reviewed by user

        Helps track which spam items have been seen

        Args:
            db: Database connection
            spam_id: Spam lead ID

        Returns:
            True if updated successfully
        """
        collection = db[SpamLeadRepository.COLLECTION_NAME]

        result = await collection.update_one(
            {"spam_id": spam_id},
            {"$set": {"user_reviewed": True}}
        )

        return result.modified_count > 0

    @staticmethod
    async def get_spam_stats(
        db: AsyncIOMotorDatabase,
        user_id: str,
        lead_form_snapshot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get spam statistics for user/form

        Returns counts by filter stage and reason

        Args:
            db: Database connection
            user_id: User ID
            lead_form_snapshot_id: Optional form filter

        Returns:
            Dictionary with spam statistics
        """
        collection = db[SpamLeadRepository.COLLECTION_NAME]

        query = {"user_id": user_id}
        if lead_form_snapshot_id:
            query["lead_form_snapshot_id"] = lead_form_snapshot_id

        # Total spam count
        total = await collection.count_documents(query)

        # Count by filter stage
        pipeline = [
            {"$match": query},
            {"$group": {"_id": "$filter_stage", "count": {"$sum": 1}}}
        ]
        by_stage = {doc["_id"]: doc["count"] async for doc in collection.aggregate(pipeline)}

        # Count by spam reason
        pipeline = [
            {"$match": query},
            {"$group": {"_id": "$spam_reason", "count": {"$sum": 1}}}
        ]
        by_reason = {doc["_id"]: doc["count"] async for doc in collection.aggregate(pipeline)}

        # Count promoted
        promoted_count = await collection.count_documents({**query, "promoted_to_leads": True})

        # Count reviewed
        reviewed_count = await collection.count_documents({**query, "user_reviewed": True})

        return {
            "total_spam": total,
            "by_filter_stage": by_stage,
            "by_spam_reason": by_reason,
            "promoted_count": promoted_count,
            "reviewed_count": reviewed_count,
            "unreviewed_count": total - reviewed_count
        }
