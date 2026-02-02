"""
CRM Sync Log Repository
Handles database operations for tracking CRM sync history

Collections:
- crm_sync_logs: Stores detailed logs of each sync operation
"""
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId


class CRMSyncLogRepository:
    """Repository for CRM sync log database operations"""

    # ============ INDEXES ============
    @staticmethod
    async def setup_indexes(db: AsyncIOMotorDatabase):
        """Setup indexes for CRM sync logs collection"""
        try:
            print("⚙️ Setting up indexes for CRM sync logs collection...")

            # User ID index
            await db["crm_sync_logs"].create_index([("user_id", 1)])

            # CRM type index
            await db["crm_sync_logs"].create_index([("crm_type", 1)])

            # Sync status index
            await db["crm_sync_logs"].create_index([("status", 1)])

            # Started at index (for sorting by date)
            await db["crm_sync_logs"].create_index([("started_at", -1)])

            # Compound index for user + date queries
            await db["crm_sync_logs"].create_index([
                ("user_id", 1),
                ("started_at", -1)
            ])

            print("✅ CRM sync logs indexes created successfully")

        except Exception as e:
            print(f"❌ Error creating CRM sync logs indexes: {str(e)}")

    # ============ CREATE LOG ============
    @staticmethod
    async def create_sync_log(
        db: AsyncIOMotorDatabase,
        user_id: str,
        crm_type: str
    ) -> Optional[str]:
        """
        Create a new sync log entry

        Args:
            db: Database connection
            user_id: User ID
            crm_type: CRM type (hubspot or salesforce)

        Returns:
            Log ID or None if failed
        """
        try:
            log_entry = {
                "user_id": user_id,
                "crm_type": crm_type,
                "status": "in_progress",
                "started_at": datetime.utcnow(),
                "completed_at": None,
                "duration_seconds": None,
                "contacts_fetched": 0,
                "contacts_added": 0,
                "contacts_skipped": 0,
                "companies_fetched": 0,
                "companies_added": 0,
                "companies_skipped": 0,
                "deals_processed": 0,
                "opportunities_processed": 0,
                "error_message": None,
                "error_code": None,
                "error_type": None,
                "created_at": datetime.utcnow(),
            }

            result = await db["crm_sync_logs"].insert_one(log_entry)
            return str(result.inserted_id)

        except Exception as e:
            print(f"Error creating sync log: {str(e)}")
            return None

    # ============ UPDATE LOG ============
    @staticmethod
    async def update_sync_log(
        db: AsyncIOMotorDatabase,
        log_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update sync log entry

        Args:
            db: Database connection
            log_id: Log entry ID
            update_data: Data to update

        Returns:
            Result with success status
        """
        try:
            result = await db["crm_sync_logs"].update_one(
                {"_id": ObjectId(log_id)},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Sync log updated",
                }
            else:
                return {
                    "success": False,
                    "message": "Sync log not found",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update sync log: {str(e)}",
            }

    # ============ COMPLETE LOG ============
    @staticmethod
    async def complete_sync_log(
        db: AsyncIOMotorDatabase,
        log_id: str,
        status: str,  # "success" or "failed"
        stats: Dict[str, int],
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark sync log as completed

        Args:
            db: Database connection
            log_id: Log entry ID
            status: "success" or "failed"
            stats: Dictionary with sync statistics
            error_message: Error message if failed
            error_code: Error code if failed
            error_type: Error type if failed

        Returns:
            Result with success status
        """
        try:
            # Get the log to calculate duration
            log = await db["crm_sync_logs"].find_one({"_id": ObjectId(log_id)})
            if not log:
                return {
                    "success": False,
                    "message": "Sync log not found",
                }

            started_at = log.get("started_at")
            completed_at = datetime.utcnow()
            duration_seconds = (completed_at - started_at).total_seconds() if started_at else None

            update_data = {
                "status": status,
                "completed_at": completed_at,
                "duration_seconds": duration_seconds,
                **stats,  # Add all stats (contacts_added, companies_added, etc.)
            }

            if error_message:
                update_data["error_message"] = error_message
                update_data["error_code"] = error_code
                update_data["error_type"] = error_type

            result = await db["crm_sync_logs"].update_one(
                {"_id": ObjectId(log_id)},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Sync log completed",
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to complete sync log",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to complete sync log: {str(e)}",
            }

    # ============ GET LOGS ============
    @staticmethod
    async def get_sync_logs_for_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get sync logs for a user

        Args:
            db: Database connection
            user_id: User ID
            limit: Maximum number of logs to return

        Returns:
            List of sync logs
        """
        try:
            cursor = db["crm_sync_logs"].find(
                {"user_id": user_id}
            ).sort("started_at", -1).limit(limit)

            logs = await cursor.to_list(length=limit)

            # Convert ObjectId to string
            for log in logs:
                log["_id"] = str(log["_id"])

            return logs

        except Exception as e:
            print(f"Error getting sync logs: {str(e)}")
            return []

    # ============ GET LATEST LOG ============
    @staticmethod
    async def get_latest_sync_log(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest sync log for a user

        Args:
            db: Database connection
            user_id: User ID

        Returns:
            Latest sync log or None
        """
        try:
            log = await db["crm_sync_logs"].find_one(
                {"user_id": user_id},
                sort=[("started_at", -1)]
            )

            if log:
                log["_id"] = str(log["_id"])
                return log

            return None

        except Exception as e:
            print(f"Error getting latest sync log: {str(e)}")
            return None

    # ============ GET STATS ============
    @staticmethod
    async def get_sync_stats(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get aggregate sync statistics for a user

        Args:
            db: Database connection
            user_id: User ID

        Returns:
            Dictionary with aggregate stats
        """
        try:
            pipeline = [
                {"$match": {"user_id": user_id, "status": "success"}},
                {
                    "$group": {
                        "_id": None,
                        "total_syncs": {"$sum": 1},
                        "total_contacts_added": {"$sum": "$contacts_added"},
                        "total_companies_added": {"$sum": "$companies_added"},
                        "avg_duration_seconds": {"$avg": "$duration_seconds"},
                    }
                }
            ]

            result = await db["crm_sync_logs"].aggregate(pipeline).to_list(length=1)

            if result:
                stats = result[0]
                del stats["_id"]
                return stats
            else:
                return {
                    "total_syncs": 0,
                    "total_contacts_added": 0,
                    "total_companies_added": 0,
                    "avg_duration_seconds": 0,
                }

        except Exception as e:
            print(f"Error getting sync stats: {str(e)}")
            return {
                "total_syncs": 0,
                "total_contacts_added": 0,
                "total_companies_added": 0,
                "avg_duration_seconds": 0,
            }
