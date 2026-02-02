"""
CRM Repository
Handles database operations for CRM connections

Collections:
- crm_connections: Stores OAuth tokens and connection metadata for HubSpot/Salesforce
"""
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId


class CRMRepository:
    """Repository for CRM connection database operations"""

    # ============ INDEXES ============
    @staticmethod
    async def setup_indexes(db: AsyncIOMotorDatabase):
        """Setup indexes for CRM connections collection"""
        try:
            print("⚙️ Setting up indexes for CRM connections collection...")

            # User ID index (one connection per user)
            await db["crm_connections"].create_index(
                [("user_id", 1)], unique=True
            )

            # CRM type index
            await db["crm_connections"].create_index([("crm_type", 1)])

            # Last sync date index (for scheduled syncs)
            await db["crm_connections"].create_index([("last_sync_at", 1)])

            print("✅ CRM connections indexes created successfully")

        except Exception as e:
            print(f"❌ Error creating CRM connections indexes: {str(e)}")

    # ============ CREATE/UPDATE ============
    @staticmethod
    async def save_crm_connection(
        db: AsyncIOMotorDatabase,
        user_id: str,
        connection_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save or update CRM connection for a user

        Args:
            db: Database connection
            user_id: User ID
            connection_data: Connection details (access_token, refresh_token, etc.)

        Returns:
            Result with success status
        """
        try:
            # Check if connection already exists
            existing = await db["crm_connections"].find_one({"user_id": user_id})

            if existing:
                # Update existing connection
                result = await db["crm_connections"].update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            **connection_data,
                            "updated_at": datetime.utcnow(),
                        }
                    }
                )
                return {
                    "success": True,
                    "message": "CRM connection updated",
                    "connection_id": str(existing["_id"]),
                }
            else:
                # Create new connection
                connection_data["created_at"] = datetime.utcnow()
                connection_data["updated_at"] = datetime.utcnow()

                result = await db["crm_connections"].insert_one(connection_data)
                return {
                    "success": True,
                    "message": "CRM connection created",
                    "connection_id": str(result.inserted_id),
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to save CRM connection: {str(e)}",
            }

    # ============ READ ============
    @staticmethod
    async def get_crm_connection(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get CRM connection for a user

        Args:
            db: Database connection
            user_id: User ID

        Returns:
            Connection data or None if not found
        """
        try:
            connection = await db["crm_connections"].find_one({"user_id": user_id})

            if connection:
                connection["_id"] = str(connection["_id"])
                return connection

            return None

        except Exception as e:
            print(f"Error getting CRM connection: {str(e)}")
            return None

    # ============ UPDATE TOKENS ============
    @staticmethod
    async def update_crm_tokens(
        db: AsyncIOMotorDatabase,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int
    ) -> Dict[str, Any]:
        """
        Update CRM access and refresh tokens (for token refresh)

        Args:
            db: Database connection
            user_id: User ID
            access_token: New access token
            refresh_token: New refresh token
            expires_in: Token expiry in seconds

        Returns:
            Result with success status
        """
        try:
            result = await db["crm_connections"].update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "expires_in": expires_in,
                        "updated_at": datetime.utcnow(),
                    }
                }
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Tokens updated successfully",
                }
            else:
                return {
                    "success": False,
                    "message": "No connection found to update",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update tokens: {str(e)}",
            }

    # ============ UPDATE SYNC STATUS ============
    @staticmethod
    async def update_last_sync(
        db: AsyncIOMotorDatabase,
        user_id: str,
        contacts_synced: int,
        companies_synced: int,
        sync_duration_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update last sync timestamp and counts

        Args:
            db: Database connection
            user_id: User ID
            contacts_synced: Number of contacts added in this sync
            companies_synced: Number of companies added in this sync
            sync_duration_seconds: Duration of sync in seconds

        Returns:
            Result with success status
        """
        try:
            # Get current connection to calculate average
            connection = await db["crm_connections"].find_one({"user_id": user_id})
            if not connection:
                return {
                    "success": False,
                    "message": "No connection found to update",
                }

            # Calculate new average sync duration
            total_syncs = connection.get("total_syncs", 0)
            avg_duration = connection.get("avg_sync_duration_seconds", 0)

            if sync_duration_seconds and total_syncs > 0:
                new_avg_duration = ((avg_duration * total_syncs) + sync_duration_seconds) / (total_syncs + 1)
            elif sync_duration_seconds:
                new_avg_duration = sync_duration_seconds
            else:
                new_avg_duration = avg_duration

            update_data = {
                "$set": {
                    "last_sync_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "last_error": None,  # Clear error on successful sync
                    "last_error_code": None,
                    "last_error_type": None,
                    "last_error_at": None,
                    "avg_sync_duration_seconds": new_avg_duration,
                },
                "$inc": {
                    "contacts_synced": contacts_synced,
                    "companies_synced": companies_synced,
                    "total_syncs": 1,
                    "successful_syncs": 1,
                }
            }

            if sync_duration_seconds:
                update_data["$set"]["last_sync_duration_seconds"] = sync_duration_seconds

            result = await db["crm_connections"].update_one(
                {"user_id": user_id},
                update_data
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Sync status updated",
                }
            else:
                return {
                    "success": False,
                    "message": "No connection found to update",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update sync status: {str(e)}",
            }

    # ============ ERROR TRACKING ============
    @staticmethod
    async def update_error_tracking(
        db: AsyncIOMotorDatabase,
        user_id: str,
        error_message: str,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track error details for CRM connection and increment failed syncs

        Args:
            db: Database connection
            user_id: User ID
            error_message: Error message
            error_code: HTTP status code or error code
            error_type: Type of error (auth_failed, rate_limit, api_error, etc.)

        Returns:
            Result with success status
        """
        try:
            result = await db["crm_connections"].update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "last_error": error_message,
                        "last_error_code": error_code,
                        "last_error_type": error_type,
                        "last_error_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    },
                    "$inc": {
                        "total_syncs": 1,
                        "failed_syncs": 1,
                    }
                }
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Error tracking updated",
                }
            else:
                return {
                    "success": False,
                    "message": "No connection found to update",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update error tracking: {str(e)}",
            }

    # ============ DELETE ============
    @staticmethod
    async def remove_crm_connection(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Remove CRM connection for a user

        Args:
            db: Database connection
            user_id: User ID

        Returns:
            Result with success status
        """
        try:
            result = await db["crm_connections"].delete_one({"user_id": user_id})

            if result.deleted_count > 0:
                return {
                    "success": True,
                    "message": "CRM connection removed successfully",
                }
            else:
                return {
                    "success": False,
                    "message": "No CRM connection found for this user",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to remove CRM connection: {str(e)}",
            }

    # ============ GET ALL CONNECTIONS (for scheduled sync) ============
    @staticmethod
    async def get_all_active_connections(
        db: AsyncIOMotorDatabase
    ) -> list[Dict[str, Any]]:
        """
        Get all active CRM connections (for scheduled background sync)

        Args:
            db: Database connection

        Returns:
            List of all CRM connections
        """
        try:
            cursor = db["crm_connections"].find({})
            connections = await cursor.to_list(length=None)

            # Convert ObjectId to string
            for conn in connections:
                conn["_id"] = str(conn["_id"])

            return connections

        except Exception as e:
            print(f"Error getting active CRM connections: {str(e)}")
            return []
