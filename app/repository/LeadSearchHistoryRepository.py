"""
Repository for Lead Search History operations
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.domain.schemas.lead_search_history_schema import (
    LeadSearchHistory,
    LeadSearchHistoryCreate,
    LeadSearchHistorySummary,
    SearchResultStats
)
from app.domain.responses.uri_response import UriResponse
from bson import ObjectId


class LeadSearchHistoryRepository:
    """Repository for managing lead search history"""

    collection_name = "lead_search_history"

    @staticmethod
    async def create(
        db: AsyncIOMotorDatabase,
        search_history: LeadSearchHistoryCreate
    ) -> Dict[str, Any]:
        """Create a new search history record"""
        try:
            search_data = search_history.dict()
            search_data["_id"] = str(ObjectId())

            await db[LeadSearchHistoryRepository.collection_name].insert_one(search_data)

            return UriResponse.create_response(
                "search_history",
                LeadSearchHistory(**search_data).dict()
            )
        except Exception as e:
            print(f"Error creating search history: {str(e)}")
            return UriResponse.error_response(f"Failed to create search history: {str(e)}")

    @staticmethod
    async def get_by_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> Dict[str, Any]:
        """Get search history for a user"""
        try:
            cursor = db[LeadSearchHistoryRepository.collection_name].find(
                {"user_id": user_id}
            ).sort("search_timestamp", -1).skip(skip).limit(limit)

            searches = await cursor.to_list(length=limit)
            search_list = [LeadSearchHistory(**search).dict() for search in searches]

            return UriResponse.get_list_data_response("search_history", search_list)
        except Exception as e:
            print(f"Error fetching search history: {str(e)}")
            return UriResponse.error_response(f"Failed to fetch search history: {str(e)}")

    @staticmethod
    async def get_by_lead_form(
        db: AsyncIOMotorDatabase,
        lead_form_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get search history for a specific lead form"""
        try:
            cursor = db[LeadSearchHistoryRepository.collection_name].find(
                {"lead_form_id": lead_form_id}
            ).sort("search_timestamp", -1).limit(limit)

            searches = await cursor.to_list(length=limit)
            search_list = [LeadSearchHistory(**search).dict() for search in searches]

            return UriResponse.get_list_data_response("search_history", search_list)
        except Exception as e:
            print(f"Error fetching search history: {str(e)}")
            return UriResponse.error_response(f"Failed to fetch search history: {str(e)}")

    @staticmethod
    async def get_recent_search(
        db: AsyncIOMotorDatabase,
        lead_form_id: str,
        keyword: str,
        hours: int = 1
    ) -> Optional[LeadSearchHistory]:
        """Check if same search was run recently"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            search = await db[LeadSearchHistoryRepository.collection_name].find_one({
                "lead_form_id": lead_form_id,
                "keyword": keyword,
                "search_timestamp": {"$gte": cutoff_time},
                "success": True
            })

            if search:
                return LeadSearchHistory(**search)
            return None
        except Exception as e:
            print(f"Error checking recent search: {str(e)}")
            return None

    @staticmethod
    async def get_summary(
        db: AsyncIOMotorDatabase,
        lead_form_id: str
    ) -> Dict[str, Any]:
        """Get summary statistics for a lead form's search history"""
        try:
            pipeline = [
                {"$match": {"lead_form_id": lead_form_id, "success": True}},
                {
                    "$group": {
                        "_id": "$lead_form_id",
                        "total_searches": {"$sum": 1},
                        "total_leads_found": {"$sum": "$results.new_leads_saved"},
                        "total_duplicates_skipped": {"$sum": "$results.duplicates_skipped"},
                        "last_search_timestamp": {"$max": "$search_timestamp"},
                        "keywords": {"$push": "$keyword"}
                    }
                }
            ]

            result = await db[LeadSearchHistoryRepository.collection_name].aggregate(pipeline).to_list(length=1)

            if not result:
                return UriResponse.get_single_data_response("summary", None)

            data = result[0]

            # Find most used keyword
            keyword_counts = {}
            for kw in data.get("keywords", []):
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            most_used_keyword = max(keyword_counts, key=keyword_counts.get) if keyword_counts else None

            # Calculate average
            total_searches = data.get("total_searches", 0)
            total_leads = data.get("total_leads_found", 0)
            avg_leads = total_leads / total_searches if total_searches > 0 else 0.0

            summary = LeadSearchHistorySummary(
                lead_form_id=lead_form_id,
                total_searches=total_searches,
                total_leads_found=total_leads,
                total_duplicates_skipped=data.get("total_duplicates_skipped", 0),
                last_search_timestamp=data.get("last_search_timestamp"),
                most_used_keyword=most_used_keyword,
                average_leads_per_search=round(avg_leads, 2)
            )

            return UriResponse.get_single_data_response("summary", summary.dict())
        except Exception as e:
            print(f"Error getting search summary: {str(e)}")
            return UriResponse.error_response(f"Failed to get summary: {str(e)}")

    @staticmethod
    async def setup_indexes(db: AsyncIOMotorDatabase):
        """Create indexes for search history collection"""
        try:
            print("⚙️ Setting up indexes for 'lead_search_history' collection...")

            # Index for user queries
            await db[LeadSearchHistoryRepository.collection_name].create_index(
                [("user_id", 1), ("search_timestamp", -1)],
                name="user_search_history"
            )

            # Index for lead form queries
            await db[LeadSearchHistoryRepository.collection_name].create_index(
                [("lead_form_id", 1), ("search_timestamp", -1)],
                name="lead_form_search_history"
            )

            # Index for duplicate search detection
            await db[LeadSearchHistoryRepository.collection_name].create_index(
                [("lead_form_id", 1), ("keyword", 1), ("search_timestamp", -1)],
                name="duplicate_search_check"
            )

            print("✅ Search history indexes created successfully.")
        except Exception as e:
            print(f"❌ Failed to set up search history indexes: {e}")

    @staticmethod
    async def delete_old_history(
        db: AsyncIOMotorDatabase,
        days: int = 90
    ) -> int:
        """Delete search history older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            result = await db[LeadSearchHistoryRepository.collection_name].delete_many({
                "search_timestamp": {"$lt": cutoff_date}
            })

            print(f"Deleted {result.deleted_count} search history records older than {days} days")
            return result.deleted_count
        except Exception as e:
            print(f"Error deleting old search history: {str(e)}")
            return 0
