# app/agents/social_media_manager/repositories/content_request_repository.py

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.domain.responses.uri_response import UriResponse


class ContentRequestRepository:
    """
    Repository for managing content generation requests
    
    Follows existing URI repository patterns and integrates with
    your current database structure and response formats.
    """
    
    @staticmethod
    async def create_request(
        db: AsyncIOMotorDatabase,
        user_id: str,
        seed_content: str,
        platforms: List[str],
        seed_type: str = "text",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new content generation request
        
        Follows your existing repository pattern for creating records
        """
        try:
            collection = db["content_requests"]
            
            if not request_id:
                request_id = str(ObjectId())
            
            request_data = {
                "id": request_id,
                "user_id": user_id,
                "seed_content": seed_content,
                "seed_type": seed_type,
                "requested_platforms": platforms,
                "status": "generating",
                "metadata": {
                    "created_via": "uri_social_media_manager",
                    "platform_count": len(platforms)
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await collection.insert_one(request_data)
            
            if result.inserted_id:
                return UriResponse.get_single_data_response(
                    "content_request", 
                    {"request_id": request_id, "status": "created"}
                )
            else:
                return UriResponse.error_response("Failed to create content request")
                
        except Exception as e:
            return UriResponse.error_response(f"Database error: {str(e)}")
    
    @staticmethod
    async def get_request_by_id(
        db: AsyncIOMotorDatabase,
        request_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get a content request by ID for a specific user
        """
        try:
            collection = db["content_requests"]
            
            request = await collection.find_one({
                "id": request_id,
                "user_id": user_id
            })
            
            if request:
                # Convert ObjectId to string for JSON serialization
                if "_id" in request:
                    del request["_id"]
                    
                return UriResponse.get_single_data_response("content_request", request)
            else:
                return UriResponse.error_response("Content request not found", code=404)
                
        except Exception as e:
            return UriResponse.error_response(f"Database error: {str(e)}")
    
    @staticmethod
    async def update_request_status(
        db: AsyncIOMotorDatabase,
        request_id: str,
        status: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Update the status of a content request
        """
        try:
            collection = db["content_requests"]
            
            result = await collection.update_one(
                {"id": request_id, "user_id": user_id},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                return UriResponse.get_single_data_response(
                    "update_result", 
                    {"request_id": request_id, "status": status}
                )
            else:
                return UriResponse.error_response("Request not found or not updated")
                
        except Exception as e:
            return UriResponse.error_response(f"Database error: {str(e)}")
    
    @staticmethod
    async def get_user_requests(
        db: AsyncIOMotorDatabase,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Get content requests for a user with optional filtering
        """
        try:
            collection = db["content_requests"]
            
            query = {"user_id": user_id}
            if status:
                query["status"] = status
            
            cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            requests = await cursor.to_list(length=limit)
            
            # Clean up ObjectIds
            for request in requests:
                if "_id" in request:
                    del request["_id"]
            
            # Get total count
            total_count = await collection.count_documents(query)
            
            return UriResponse.get_single_data_response("user_requests", {
                "requests": requests,
                "total_count": total_count,
                "page_info": {
                    "skip": skip,
                    "limit": limit,
                    "has_more": (skip + limit) < total_count
                }
            })
            
        except Exception as e:
            return UriResponse.error_response(f"Database error: {str(e)}")
    
    @staticmethod
    async def get_monthly_request_count(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> int:
        """
        Get the number of content requests for the current month
        Used for feature limit checking
        """
        try:
            collection = db["content_requests"]
            
            # Get start of current month
            now = datetime.utcnow()
            start_of_month = datetime(now.year, now.month, 1)
            
            count = await collection.count_documents({
                "user_id": user_id,
                "created_at": {"$gte": start_of_month}
            })
            
            return count
            
        except Exception as e:
            print(f"Error getting monthly request count: {str(e)}")
            return 0
    
    @staticmethod
    async def cleanup_old_requests(
        db: AsyncIOMotorDatabase,
        days_old: int = 30
    ) -> Dict[str, Any]:
        """
        Clean up old requests (for maintenance)
        """
        try:
            collection = db["content_requests"]
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await collection.delete_many({
                "created_at": {"$lt": cutoff_date},
                "status": {"$in": ["failed", "published"]}
            })
            
            return UriResponse.get_single_data_response(
                "cleanup_result", 
                {"deleted_count": result.deleted_count}
            )
            
        except Exception as e:
            return UriResponse.error_response(f"Cleanup failed: {str(e)}")