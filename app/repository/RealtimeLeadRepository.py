from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.domain.schemas.realtime_lead_schema import RealtimeLead, RealtimeLeadUpdate, RealtimeLeadBatch
from app.core.helpers.mongo_helper import MongoHelper


class RealtimeLeadRepository:
    collection_name = "realtime_leads"

    @staticmethod
    async def create_lead(db: AsyncIOMotorDatabase, lead: RealtimeLead) -> dict:
        """Create a new realtime lead."""
        lead_dict = lead.dict()
        result = await db[RealtimeLeadRepository.collection_name].insert_one(lead_dict)
        lead_dict["_id"] = result.inserted_id
        return {"status": True, "responseData": lead_dict}

    @staticmethod
    async def create_many(db: AsyncIOMotorDatabase, leads: List[RealtimeLead]) -> dict:
        """Create multiple realtime leads."""
        if not leads:
            return {"status": True, "responseData": {"leads": [], "count": 0}}

        leads_dict = [lead.dict() for lead in leads]
        result = await db[RealtimeLeadRepository.collection_name].insert_many(leads_dict)
        
        return {
            "status": True,
            "responseData": {
                "leads": leads_dict,
                "count": len(result.inserted_ids)
            }
        }

    @staticmethod
    async def update_lead(
        db: AsyncIOMotorDatabase,
        lead_id: str,
        update: RealtimeLeadUpdate
    ) -> dict:
        """Update a realtime lead."""
        update_dict = update.dict(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()

        result = await db[RealtimeLeadRepository.collection_name].find_one_and_update(
            {"lead_id": lead_id},
            {"$set": update_dict},
            return_document=True
        )

        if not result:
            return {"status": False, "message": f"Lead {lead_id} not found"}

        return {"status": True, "responseData": result}

    @staticmethod
    async def get_lead_by_id(db: AsyncIOMotorDatabase, lead_id: str) -> dict:
        """Get a realtime lead by ID."""
        result = await db[RealtimeLeadRepository.collection_name].find_one(
            {"lead_id": lead_id}
        )

        if not result:
            return {"status": False, "message": f"Lead {lead_id} not found"}

        return {"status": True, "responseData": result}

    @staticmethod
    async def get_leads_by_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> dict:
        """Get realtime leads for a specific user."""
        query = {"user_id": user_id}
        if status:
            query["status"] = status

        cursor = db[RealtimeLeadRepository.collection_name].find(query)
        total = await db[RealtimeLeadRepository.collection_name].count_documents(query)
        
        leads = await MongoHelper.paginate_cursor(cursor, skip, limit)
        
        return {
            "status": True,
            "responseData": {
                "leads": leads,
                "total": total,
                "skip": skip,
                "limit": limit
            }
        }

    @staticmethod
    async def save_lead_batch(
        db: AsyncIOMotorDatabase,
        batch: RealtimeLeadBatch
    ) -> dict:
        """Save a batch of realtime leads."""
        leads_result = await RealtimeLeadRepository.create_many(db, batch.leads)
        
        if not leads_result["status"]:
            return leads_result

        batch_dict = batch.dict()
        batch_dict["created_at"] = datetime.utcnow()
        
        await db["realtime_lead_batches"].insert_one(batch_dict)
        
        return leads_result

    @staticmethod
    async def get_recent_leads(
        db: AsyncIOMotorDatabase,
        minutes: int = 5,
        limit: int = 100
    ) -> dict:
        """Get recent realtime leads from the last X minutes."""
        query = {
            "created_at": {
                "$gte": datetime.utcnow().timestamp() - (minutes * 60)
            }
        }

        cursor = db[RealtimeLeadRepository.collection_name].find(query)
        leads = await MongoHelper.paginate_cursor(cursor, 0, limit)

        return {
            "status": True,
            "responseData": leads
        }