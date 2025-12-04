"""
LeadGenerationJobRepository - Track async lead generation job status
"""
from datetime import datetime
from typing import Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid


class LeadGenerationJobRepository:
    """Repository for tracking lead generation job status"""

    COLLECTION_NAME = "lead_generation_jobs"

    @staticmethod
    async def create_job(
        db: AsyncIOMotorDatabase,
        lead_form_id: str,
        user_id: str,
        status: str = "processing",
        progress: int = 0,
        message: str = "Starting lead generation..."
    ) -> str:
        """
        Create a new job tracking document.

        Returns:
            job_id: Unique job identifier for polling
        """
        job_id = str(uuid.uuid4())

        job_doc = {
            "job_id": job_id,
            "lead_form_id": lead_form_id,
            "user_id": user_id,
            "status": status,  # processing, completed, failed
            "progress": progress,  # 0-100
            "message": message,
            "stats": None,
            "error": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        await db[LeadGenerationJobRepository.COLLECTION_NAME].insert_one(job_doc)
        return job_id

    @staticmethod
    async def update_job(
        db: AsyncIOMotorDatabase,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        stats: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Update job status/progress"""
        update_fields = {"updated_at": datetime.utcnow()}

        if status is not None:
            update_fields["status"] = status
        if progress is not None:
            update_fields["progress"] = progress
        if message is not None:
            update_fields["message"] = message
        if stats is not None:
            update_fields["stats"] = stats
        if error is not None:
            update_fields["error"] = error

        await db[LeadGenerationJobRepository.COLLECTION_NAME].update_one(
            {"job_id": job_id},
            {"$set": update_fields}
        )

    @staticmethod
    async def get_job_status(
        db: AsyncIOMotorDatabase,
        job_id: str
    ) -> Optional[Dict]:
        """Get current job status for polling"""
        job = await db[LeadGenerationJobRepository.COLLECTION_NAME].find_one(
            {"job_id": job_id}
        )

        if not job:
            return None

        return {
            "job_id": job["job_id"],
            "lead_form_id": job["lead_form_id"],
            "user_id": job["user_id"],
            "status": job["status"],
            "progress": job["progress"],
            "message": job["message"],
            "stats": job.get("stats"),
            "error": job.get("error"),
            "created_at": job["created_at"].isoformat() if job.get("created_at") else None,
            "updated_at": job["updated_at"].isoformat() if job.get("updated_at") else None
        }

    @staticmethod
    async def cleanup_old_jobs(db: AsyncIOMotorDatabase, days: int = 7):
        """Clean up job records older than X days"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await db[LeadGenerationJobRepository.COLLECTION_NAME].delete_many(
            {"created_at": {"$lt": cutoff_date}}
        )
        return result.deleted_count
