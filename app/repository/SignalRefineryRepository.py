"""
Signal Refinery Repository - MongoDB storage for X-Ray test system

Collections:
- signal_refinery_jobs: Search jobs and their status
- signal_refinery_leads: Final buyer leads (separate from main leads collection)

This is ISOLATED from your existing lead system for safe testing.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging

from app.domain.schemas.signal_refinery_schema import (
    XRaySearchJob,
    XRayLead,
    XRaySearchRequest,
    RefineryMetrics
)

logger = logging.getLogger(__name__)


class SignalRefineryRepository:
    """Repository for Signal Refinery data"""

    # Collection names (separate from existing system)
    JOBS_COLLECTION = "signal_refinery_jobs"
    LEADS_COLLECTION = "signal_refinery_leads"

    @staticmethod
    async def create_job(
        db: AsyncIOMotorDatabase,
        user_id: str,
        request: XRaySearchRequest
    ) -> str:
        """
        Create a new X-Ray search job

        Returns:
            job_id
        """
        try:
            job = XRaySearchJob(
                user_id=user_id,
                request=request,
                status="pending",
                progress=0,
                current_step="Initializing..."
            )

            # Convert to dict for MongoDB
            job_dict = job.dict()

            # Insert into database
            result = await db[SignalRefineryRepository.JOBS_COLLECTION].insert_one(job_dict)

            logger.info(f"✅ Created Signal Refinery job: {job.job_id}")
            return job.job_id

        except Exception as e:
            logger.error(f"❌ Error creating Signal Refinery job: {str(e)}")
            raise

    @staticmethod
    async def get_job(
        db: AsyncIOMotorDatabase,
        job_id: str
    ) -> Optional[XRaySearchJob]:
        """Get job by ID"""
        try:
            job_dict = await db[SignalRefineryRepository.JOBS_COLLECTION].find_one(
                {"job_id": job_id}
            )

            if not job_dict:
                return None

            # Remove MongoDB _id field
            job_dict.pop("_id", None)

            return XRaySearchJob(**job_dict)

        except Exception as e:
            logger.error(f"❌ Error getting job {job_id}: {str(e)}")
            return None

    @staticmethod
    async def update_job_progress(
        db: AsyncIOMotorDatabase,
        job_id: str,
        progress: int,
        current_step: str,
        status: Optional[str] = None
    ):
        """Update job progress"""
        try:
            update_data = {
                "progress": progress,
                "current_step": current_step
            }

            if status:
                update_data["status"] = status

            if status == "running" and progress == 0:
                update_data["started_at"] = datetime.utcnow()

            await db[SignalRefineryRepository.JOBS_COLLECTION].update_one(
                {"job_id": job_id},
                {"$set": update_data}
            )

        except Exception as e:
            logger.error(f"❌ Error updating job progress: {str(e)}")

    @staticmethod
    async def complete_job(
        db: AsyncIOMotorDatabase,
        job_id: str,
        leads: List[XRayLead],
        metrics: RefineryMetrics,
        results: List[Dict[str, Any]],
        filtered: List[Dict[str, Any]]
    ):
        """Mark job as completed with results"""
        try:
            # Convert leads to dicts
            leads_dicts = [lead.dict() for lead in leads]

            await db[SignalRefineryRepository.JOBS_COLLECTION].update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": "completed",
                        "progress": 100,
                        "current_step": "Complete",
                        "completed_at": datetime.utcnow(),
                        "leads": leads_dicts,
                        "metrics": metrics.dict(),
                        "results": results,
                        "filtered": filtered
                    }
                }
            )

            logger.info(f"✅ Completed job {job_id}: {len(leads)} leads")

        except Exception as e:
            logger.error(f"❌ Error completing job: {str(e)}")
            raise

    @staticmethod
    async def fail_job(
        db: AsyncIOMotorDatabase,
        job_id: str,
        error_message: str
    ):
        """Mark job as failed"""
        try:
            await db[SignalRefineryRepository.JOBS_COLLECTION].update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "error_message": error_message,
                        "completed_at": datetime.utcnow()
                    }
                }
            )

            logger.error(f"❌ Failed job {job_id}: {error_message}")

        except Exception as e:
            logger.error(f"❌ Error failing job: {str(e)}")

    @staticmethod
    async def save_leads(
        db: AsyncIOMotorDatabase,
        leads: List[XRayLead]
    ) -> int:
        """
        Save leads to signal_refinery_leads collection

        Returns:
            Number of leads saved
        """
        if not leads:
            return 0

        try:
            # Convert to dicts
            leads_dicts = [lead.dict() for lead in leads]

            # Insert all leads
            result = await db[SignalRefineryRepository.LEADS_COLLECTION].insert_many(leads_dicts)

            logger.info(f"✅ Saved {len(result.inserted_ids)} Signal Refinery leads")
            return len(result.inserted_ids)

        except Exception as e:
            logger.error(f"❌ Error saving leads: {str(e)}")
            return 0

    @staticmethod
    async def get_leads_by_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[XRayLead]:
        """Get all leads for a user"""
        try:
            cursor = db[SignalRefineryRepository.LEADS_COLLECTION].find(
                {"user_id": user_id}
            ).sort("created_at", -1).skip(skip).limit(limit)

            leads_dicts = await cursor.to_list(length=limit)

            # Remove MongoDB _id
            for lead_dict in leads_dicts:
                lead_dict.pop("_id", None)

            leads = [XRayLead(**lead_dict) for lead_dict in leads_dicts]
            return leads

        except Exception as e:
            logger.error(f"❌ Error getting leads: {str(e)}")
            return []

    @staticmethod
    async def get_jobs_by_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[XRaySearchJob]:
        """Get all jobs for a user"""
        try:
            cursor = db[SignalRefineryRepository.JOBS_COLLECTION].find(
                {"user_id": user_id}
            ).sort("created_at", -1).skip(skip).limit(limit)

            jobs_dicts = await cursor.to_list(length=limit)

            # Remove MongoDB _id
            for job_dict in jobs_dicts:
                job_dict.pop("_id", None)

            jobs = [XRaySearchJob(**job_dict) for job_dict in jobs_dicts]
            return jobs

        except Exception as e:
            logger.error(f"❌ Error getting jobs: {str(e)}")
            return []

    @staticmethod
    async def delete_job(
        db: AsyncIOMotorDatabase,
        job_id: str,
        user_id: str
    ) -> bool:
        """Delete a job (for cleanup)"""
        try:
            result = await db[SignalRefineryRepository.JOBS_COLLECTION].delete_one(
                {"job_id": job_id, "user_id": user_id}
            )

            if result.deleted_count > 0:
                logger.info(f"✅ Deleted job {job_id}")
                return True
            else:
                logger.warning(f"⚠️ Job {job_id} not found or not owned by user")
                return False

        except Exception as e:
            logger.error(f"❌ Error deleting job: {str(e)}")
            return False

    @staticmethod
    async def get_metrics_summary(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get summary metrics across all jobs for a user

        Returns aggregate statistics
        """
        try:
            # Aggregate pipeline
            pipeline = [
                {"$match": {"user_id": user_id, "status": "completed"}},
                {
                    "$group": {
                        "_id": None,
                        "total_jobs": {"$sum": 1},
                        "total_leads": {"$sum": {"$size": "$leads"}},
                        "total_cost": {"$sum": "$metrics.total_cost"},
                        "avg_buyer_ratio": {"$avg": "$metrics.buyer_seller_ratio"},
                        "avg_spam_ratio": {"$avg": "$metrics.spam_ratio"},
                        "avg_cost_per_lead": {"$avg": "$metrics.cost_per_lead"}
                    }
                }
            ]

            result = await db[SignalRefineryRepository.JOBS_COLLECTION].aggregate(pipeline).to_list(length=1)

            if result:
                summary = result[0]
                summary.pop("_id")
                return summary
            else:
                return {
                    "total_jobs": 0,
                    "total_leads": 0,
                    "total_cost": 0.0,
                    "avg_buyer_ratio": 0.0,
                    "avg_spam_ratio": 0.0,
                    "avg_cost_per_lead": 0.0
                }

        except Exception as e:
            logger.error(f"❌ Error getting metrics summary: {str(e)}")
            return {}
