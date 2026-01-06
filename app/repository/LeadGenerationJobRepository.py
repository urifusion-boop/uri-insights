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
    async def ensure_indexes(db: AsyncIOMotorDatabase):
        """Ensure indexes exist for fast queries"""
        collection = db[LeadGenerationJobRepository.COLLECTION_NAME]

        # Create index on job_id for fast lookups
        await collection.create_index("job_id", unique=True)

        # Create index on user_id for user-specific queries
        await collection.create_index("user_id")

        # Create index on created_at for cleanup queries
        await collection.create_index("created_at")

        print(f"✅ Indexes created for {LeadGenerationJobRepository.COLLECTION_NAME}")

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
    async def mark_cancellation_requested(
        db: AsyncIOMotorDatabase,
        job_id: str
    ) -> bool:
        """
        Mark job for cancellation. Worker will detect and stop gracefully.

        Returns:
            True if cancellation request was accepted (job was cancellable)
            False if job already completed/failed or not found
        """
        job = await db[LeadGenerationJobRepository.COLLECTION_NAME].find_one(
            {"job_id": job_id}
        )

        if not job:
            return False

        # Only allow cancellation of queued/processing jobs
        if job["status"] not in ["queued", "processing"]:
            return False

        # Atomically update to cancelling (prevent race conditions)
        result = await db[LeadGenerationJobRepository.COLLECTION_NAME].update_one(
            {
                "job_id": job_id,
                "status": {"$in": ["queued", "processing"]}
            },
            {
                "$set": {
                    "status": "cancelling",
                    "message": "Cancellation requested by user",
                    "cancellation_requested_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    @staticmethod
    async def mark_cancelled(
        db: AsyncIOMotorDatabase,
        job_id: str,
        partial_stats: Dict,
        processed_count: int
    ) -> None:
        """
        Mark job as fully cancelled with partial results.
        Called by worker after graceful exit.
        """
        await db[LeadGenerationJobRepository.COLLECTION_NAME].update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": "cancelled",
                    "progress": 100,
                    "message": f"Cancelled by user after processing {processed_count} items",
                    "stats": partial_stats,
                    "cancelled_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

    @staticmethod
    async def cleanup_old_jobs(db: AsyncIOMotorDatabase, days: int = 7):
        """Clean up job records older than X days"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await db[LeadGenerationJobRepository.COLLECTION_NAME].delete_many(
            {"created_at": {"$lt": cutoff_date}}
        )
        return result.deleted_count
