from collections import defaultdict
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime

import pymongo
import pymongo.errors
from app.core.helpers.lead_helper import LeadHelper
from app.domain.enums.lead_enum import LeadStatusEnum
from app.domain.schemas.lead_schema import (
    Lead,
    LeadCreate,
    LeadUpdate,
)
from app.domain.responses.uri_response import UriResponse
from app.domain.responses.lead_response import LeadAnalyticsResponse
from app.core.helpers.date_helper import DateHelper
from app.domain.requests.lead_requests import (
    GetLeadsByFiltersRequest,
    LeadAnalyticsRequest,
)
from app.domain.enums.date_enum import DateFilterEnum


class LeadRepository:
    @staticmethod
    async def delete_duplicate_leads(db: AsyncIOMotorDatabase):
        print("🚨 Checking for duplicate leads...")

        pipeline = [
            {
                "$group": {
                    "_id": {
                        "assigned_to": "$assigned_to",
                        "lead_source": "$lead_source",
                        "lead_link": "$lead_link",
                        "username": "$username",
                    },
                    "ids": {"$push": "$_id"},
                    "count": {"$sum": 1},
                }
            },
            {"$match": {"count": {"$gt": 1}}},
        ]

        duplicates = db["leads"].aggregate(pipeline)

        deleted_count = 0
        async for group in duplicates:
            ids = group["ids"]
            ids_to_delete = ids[1:]  # keep the first, delete the rest

            result = await db["leads"].delete_many({"_id": {"$in": ids_to_delete}})
            deleted_count += result.deleted_count
            print(
                f"🗑️ Deleted {result.deleted_count} duplicates for group: {group['_id']}"
            )

        print(f"✅ Done. Total duplicates removed: {deleted_count}")

    @staticmethod
    async def setup_indexes(db: AsyncIOMotorDatabase):
        try:
            print("⚙️ Setting up indexes for 'Leads' collection...")
            await db["leads"].create_index(
                [
                    ("assigned_to", 1),
                    ("lead_source", 1),
                    ("lead_link", 1),
                    ("username", 1),
                ],
                unique=True,
                sparse=True,
            )

            # Duplicate detection index for conversational leads (URL-based)
            # Prevents same post URL from being saved multiple times for the same user
            await db["leads"].create_index(
                [
                    ("lead_link", 1),
                    ("assigned_to", 1),
                ],
                name="lead_link_user_duplicate_check",
                sparse=True,
            )

            # Duplicate detection index for conversational leads (content-based)
            # Prevents retweets/shares with same content from being saved multiple times
            await db["leads"].create_index(
                [
                    ("content_hash", 1),
                    ("assigned_to", 1),
                ],
                name="content_hash_user_duplicate_check",
                sparse=True,
            )

            print("✅ Indexes created successfully.")
        except Exception as e:
            print("❌ Failed to set up indexes: ", e)

    @staticmethod
    async def update_conv_to_biz_leads(db: AsyncIOMotorDatabase):
        print("🔄 Updating all CONVERSATIONAL leads to BUSINESS...")

        try:
            result = await db["leads"].update_many(
                {"lead_type": "CONVERSATIONAL"},  # filter
                {
                    "$set": {"lead_type": "BUSINESS", "last_updated": datetime.utcnow()}
                },  # update
            )

            print(
                f"✅ Updated {result.modified_count} leads "
                f"(matched {result.matched_count}) from CONVERSATIONAL to BUSINESS."
            )
        except Exception as e:
            print("❌ Failed to update leads:", e)

    @staticmethod
    async def create_lead(db: AsyncIOMotorDatabase, lead: LeadCreate) -> Dict[str, Any]:
        lead_data = lead.dict()
        lead_data["lead_id"] = str(ObjectId())
        lead_data["created_date"] = DateHelper.utc_now_iso()
        lead_data["last_updated"] = DateHelper.utc_now_iso()
        lead_data["username"] = LeadHelper.cleanup_lead_username(lead.username)

        # Check for duplicates by lead_link (post URL) and assigned_to (user_id)
        # This prevents same post from being saved multiple times for same user
        if lead.lead_link and lead.assigned_to:
            existing_lead = await db["leads"].find_one({
                "lead_link": lead.lead_link,
                "assigned_to": lead.assigned_to
            })
            if existing_lead:
                return UriResponse.conflict_response("lead", "Lead already exists")

        await db["leads"].insert_one(lead_data)
        return UriResponse.create_response("lead", Lead(**lead_data).dict())

    @staticmethod
    async def update_lead(
        db: AsyncIOMotorDatabase, lead_id: str, updates: LeadUpdate
    ) -> Dict[str, Any]:
        updates_data = updates.dict(exclude_unset=True)
        updates_data["last_updated"] = DateHelper.utc_now_iso()

        result = await db["leads"].update_one(
            {"lead_id": lead_id}, {"$set": updates_data}
        )

        if result.matched_count == 0:
            return UriResponse.get_single_data_response("lead", None)

        updated_lead = await db["leads"].find_one({"lead_id": lead_id})
        return UriResponse.update_response("lead", Lead(**updated_lead).dict())

    @staticmethod
    async def update_many_leads(
        db: AsyncIOMotorDatabase, lead_ids: List[str], updates: LeadUpdate
    ) -> dict[str, Any]:
        updates_data = updates.dict(exclude_unset=True)
        updates_data["last_updated"] = DateHelper.utc_now_iso()

        # Perform bulk update
        result = await db["leads"].update_many(
            {"lead_id": {"$in": lead_ids}}, {"$set": updates_data}
        )

        if result.matched_count == 0:
            return UriResponse.get_list_data_response("leads", [])

        # Fetch updated leads
        updated_leads_cursor = db["leads"].find({"lead_id": {"$in": lead_ids}})
        updated_leads = [
            Lead(**lead).model_dump(mode="json") async for lead in updated_leads_cursor
        ]

        return UriResponse.update_response("leads", updated_leads)

    @staticmethod
    async def get_lead_by_id(db: AsyncIOMotorDatabase, lead_id: str) -> Dict[str, Any]:
        lead = await db["leads"].find_one({"lead_id": lead_id})
        return UriResponse.get_single_data_response(
            "lead", Lead(**lead).dict() if lead else None
        )

    @staticmethod
    async def get_leads_by_filters(
        db: AsyncIOMotorDatabase,
        filters: GetLeadsByFiltersRequest,
        date_filter: Optional[DateFilterEnum] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        query: Dict[str, Any] = filters.model_dump(exclude_none=True)

        if date_filter:
            start_date, end_date = DateHelper.get_date_range(date_filter)
            query["created_date"] = {
                "$gte": start_date.isoformat(),
                "$lte": end_date.isoformat(),
            }

        if not filters.is_pre_stored:
            query["$or"] = [
                {"is_pre_stored": False},
                {"is_pre_stored": {"$exists": False}},
            ]

        total_leads = await db["leads"].count_documents(query)
        leads = (
            await db["leads"]
            .find(query)
            .sort("last_updated", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )

        leads_list = [Lead(**lead).dict() for lead in leads]
        return UriResponse.get_paged_data_response(
            "leads", leads_list, total_leads, skip + 1, limit
        )

    @staticmethod
    async def get_leads_count_by_filter(
        db: AsyncIOMotorDatabase,
        filters: Dict[str, Any],
    ):
        filters["is_pre_stored"] = False
        total_leads = await db["leads"].count_documents(filters)
        return UriResponse.get_single_data_response("leads count", total_leads)

    @staticmethod
    async def get_leads_count_for_subscription_period(
        db: AsyncIOMotorDatabase,
        assigned_to: str,
        start_date,
    ):
        query = {
            "assigned_to": assigned_to,
            "is_pre_stored": False,
            "created_date": {"$gte": start_date},
        }
        total_leads = await db["leads"].count_documents(query)
        return UriResponse.get_single_data_response("leads count", total_leads)

    @staticmethod
    async def delete_lead(db: AsyncIOMotorDatabase, lead_id: str) -> Dict[str, Any]:
        deleted_lead = await db["leads"].find_one_and_delete({"lead_id": lead_id})
        if not deleted_lead:
            return UriResponse.delete_response("lead", False, "Lead not found.")
        return UriResponse.delete_response(
            "lead", True, data=Lead(**deleted_lead).model_dump(mode="json")
        )

    @staticmethod
    async def delete_many_leads(db: AsyncIOMotorDatabase, lead_ids: List[str]):
        result = await db["leads"].delete_many({"lead_id": {"$in": lead_ids}})
        if result.deleted_count == 0:
            return UriResponse.delete_response("lead", False, "Leads not found.")
        return UriResponse.delete_response("lead", True)

    @staticmethod
    async def delete_all_leads_for_user(
        db: AsyncIOMotorDatabase, user_id: str
    ) -> Dict[str, Any]:
        result = await db["leads"].delete_many({"assigned_to": user_id})
        if result.deleted_count == 0:
            return UriResponse.delete_response("lead", False, "Leads not found.")
        return UriResponse.delete_response("lead", True)

    @staticmethod
    async def multiple_create_leads(
        db: AsyncIOMotorDatabase, leads: List[LeadCreate]
    ) -> Dict[str, Any]:
        lead_data_list = []
        id_to_lead_map = {}
        skipped_count = 0

        # Build list of existing lead_link + assigned_to combinations AND content_hash for this user
        user_lead_links = {}
        user_content_hashes = {}
        for lead in leads:
            if lead.lead_link and lead.assigned_to:
                if lead.assigned_to not in user_lead_links:
                    user_lead_links[lead.assigned_to] = []
                user_lead_links[lead.assigned_to].append(lead.lead_link)

            # Also track content hashes for content-based deduplication
            if lead.content_hash and lead.assigned_to:
                if lead.assigned_to not in user_content_hashes:
                    user_content_hashes[lead.assigned_to] = []
                user_content_hashes[lead.assigned_to].append(lead.content_hash)

        # Fetch all existing leads for these users with these links OR content hashes in one query
        existing_leads_by_user = {}
        existing_hashes_by_user = {}
        for user_id, links in user_lead_links.items():
            # Build query to check both lead_link and content_hash
            query_conditions = [
                {"assigned_to": user_id, "lead_link": {"$in": links}}
            ]

            # Add content_hash check if available
            if user_id in user_content_hashes:
                query_conditions.append({
                    "assigned_to": user_id,
                    "content_hash": {"$in": user_content_hashes[user_id], "$ne": None, "$ne": ""}
                })

            existing = await db["leads"].find({
                "$or": query_conditions
            }).to_list(length=None)

            existing_leads_by_user[user_id] = {lead["lead_link"] for lead in existing if lead.get("lead_link")}
            existing_hashes_by_user[user_id] = {lead["content_hash"] for lead in existing if lead.get("content_hash")}

        for lead in leads:
            lead_data = lead.dict()

            # Check if this lead already exists for this user (URL-based)
            if lead.lead_link and lead.assigned_to:
                if lead.lead_link in existing_leads_by_user.get(lead.assigned_to, set()):
                    skipped_count += 1
                    print(f"⏭️ Skipping duplicate URL: {lead.lead_link} for user {lead.assigned_to}")
                    continue

            # Check if this lead already exists for this user (content-based)
            if lead.content_hash and lead.assigned_to:
                if lead.content_hash in existing_hashes_by_user.get(lead.assigned_to, set()):
                    skipped_count += 1
                    print(f"⏭️ Skipping duplicate content (hash: {lead.content_hash[:8]}...) for user {lead.assigned_to}")
                    continue

            # Generate lead_id if not present
            if not lead_data.get("lead_id"):
                lead_data["lead_id"] = str(ObjectId())
            lead_data["created_date"] = DateHelper.utc_now_iso()
            lead_data["last_updated"] = DateHelper.utc_now_iso()
            lead_data["username"] = LeadHelper.cleanup_lead_username(lead.username)

            lead_data_list.append(lead_data)
            id_to_lead_map[lead_data["lead_id"]] = lead_data

        inserted_ids = []
        failed_ids = []

        # Only attempt insert if we have non-duplicate leads
        if lead_data_list:
            try:
                result = await db["leads"].insert_many(lead_data_list, ordered=False)
                inserted_ids = [str(_id) for _id in result.inserted_ids]
            except pymongo.errors.BulkWriteError as e:
                print("Error in bulk lead creation: ", e)
                write_errors = e.details.get("writeErrors", [])
                failed_ids = [str(err["op"].get("lead_id")) for err in write_errors]
                # Determine which were successfully inserted
                attempted_ids = [str(lead["lead_id"]) for lead in lead_data_list]
                inserted_ids = list(set(attempted_ids) - set(failed_ids))

        successful_leads = [
            Lead(**id_to_lead_map.get(_id, {})).dict()
            for _id in inserted_ids
            if Lead(**id_to_lead_map.get(_id, {}))
        ]

        response_payload = {
            "total_requested": len(leads),
            "successful_count": len(successful_leads),
            "skipped_duplicates": skipped_count,
            "failed_count": len(failed_ids),
            "leads": successful_leads,
        }

        message = "All leads created successfully"
        if skipped_count > 0 and failed_ids:
            message = f"Leads processed: {len(successful_leads)} created, {skipped_count} duplicates skipped, {len(failed_ids)} failed"
        elif skipped_count > 0:
            message = f"{len(successful_leads)} leads created, {skipped_count} duplicates skipped"
        elif failed_ids:
            message = "Leads processed with partial success"

        return UriResponse.custom_response(
            message=message,
            data=response_payload,
            error_code=207 if failed_ids else 201,
            success=True,
        )

    @staticmethod
    async def update_emailed(db: AsyncIOMotorDatabase, lead_id: str, status: bool):
        result = await db["leads"].update_one(
            {"lead_id": lead_id},
            {
                "$set": {
                    "emailed": status,
                    "last_updated": DateHelper.utc_now_iso(),
                }
            },
        )

        if result.matched_count == 0:
            return UriResponse.get_single_data_response("lead", None, "Lead not found.")
        updated_lead = await db["leads"].find_one({"lead_id": lead_id})
        return UriResponse.update_response("lead", Lead(**updated_lead).dict())

    @staticmethod
    async def update_called(db: AsyncIOMotorDatabase, lead_id: str, status: bool):
        result = await db["leads"].update_one(
            {"lead_id": lead_id},
            {
                "$set": {
                    "called": status,
                    "last_updated": DateHelper.utc_now_iso(),
                }
            },
        )

        if result.matched_count == 0:
            return UriResponse.get_single_data_response("lead", None, "Lead not found.")
        updated_lead = await db["leads"].find_one({"lead_id": lead_id})
        return UriResponse.update_response("lead", Lead(**updated_lead).dict())

    @staticmethod
    async def update_lead_status(
        db: AsyncIOMotorDatabase, lead_id: str, status: str
    ) -> Dict[str, Any]:
        result = await db["leads"].update_one(
            {"lead_id": lead_id},
            {
                "$set": {
                    "lead_status": status,
                    "last_updated": DateHelper.utc_now_iso(),
                }
            },
        )
        if result.matched_count == 0:
            return UriResponse.get_single_data_response("lead", None, "Lead not found.")

        updated_lead = await db["leads"].find_one({"lead_id": lead_id})
        return UriResponse.update_response("lead", Lead(**updated_lead).dict())

    @staticmethod
    async def star_lead(db: AsyncIOMotorDatabase, lead_id: str) -> Dict[str, Any]:
        updated_lead = await db["leads"].find_one_and_update(
            {"lead_id": lead_id}, {"$set": {"starred": True}}, return_document=True
        )
        if not updated_lead:
            return UriResponse.get_single_data_response("lead", None, "Lead not found.")
        return UriResponse.update_response("lead", Lead(**updated_lead).dict())

    @staticmethod
    async def unstar_lead(db: AsyncIOMotorDatabase, lead_id: str) -> Dict[str, Any]:
        updated_lead = await db["leads"].find_one_and_update(
            {"lead_id": lead_id}, {"$set": {"starred": False}}, return_document=True
        )
        if not updated_lead:
            return UriResponse.get_single_data_response("lead", None, "Lead not found.")
        return UriResponse.update_response("lead", Lead(**updated_lead).dict())

    @staticmethod
    async def search_leads(
        db: AsyncIOMotorDatabase, query: str, skip: int = 0, limit: int = 10
    ):
        search_query = {
            "$or": [
                {"first_name": {"$regex": query, "$options": "i"}},
                {"last_name": {"$regex": query, "$options": "i"}},
                {"email": {"$regex": query, "$options": "i"}},
                {"notes": {"$regex": query, "$options": "i"}},
                {"company_name": {"$regex": query, "$options": "i"}},
            ]
        }

        total = await db["leads"].count_documents(search_query)
        leads = (
            await db["leads"]
            .find(search_query)
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        leads_list = [Lead(**lead).dict() for lead in leads]
        return UriResponse.get_paged_data_response(
            "leads", leads_list, total, skip + 1, limit
        )

    @staticmethod
    async def fetch_lead_analytics(
        db: AsyncIOMotorDatabase, request: LeadAnalyticsRequest
    ):
        if request.date_filter:
            start_date, end_date = DateHelper.get_date_range(request.date_filter)

        query: dict = {}
        if request.user_id:
            query["assigned_to"] = request.user_id
        if start_date and end_date:
            query["created_date"] = {
                "$gte": start_date.isoformat(),
                "$lte": end_date.isoformat(),
            }
        if request.lead_type:
            query["lead_type"] = request.lead_type.value

        query["is_pre_stored"] = False

        leads = await db["leads"].find(query).to_list(length=1000)

        new_leads = contacted = qualified = unqualified = converted = 0
        lead_sources_breakdown: dict = defaultdict(int)
        leads_by_industry: dict = defaultdict(int)
        interest_by_platform: dict = defaultdict(lambda: defaultdict(int))

        for lead in leads:
            lead_status = lead.get("lead_status", LeadStatusEnum.NEW.value).lower()
            lead_source = lead.get("lead_source", "Unknown")
            industry = lead.get("industry", "Unknown")

            if lead_status == "new":
                new_leads += 1
            elif lead_status == "contacted":
                contacted += 1
            elif lead_status == "qualified":
                qualified += 1
            elif lead_status == "unqualified":
                unqualified += 1
            elif lead_status == "converted":
                converted += 1

            lead_sources_breakdown[lead_source] += 1
            leads_by_industry[industry] += 1
            interest_by_platform[industry][lead_source] += 1

        formatted_interest_by_platform = {
            industry: dict(platforms)
            for industry, platforms in interest_by_platform.items()
        }

        lead_analytics = LeadAnalyticsResponse(
            new_leads=new_leads,
            contacted=contacted,
            qualified=qualified,
            unqualified=unqualified,
            converted=converted,
            lead_sources_breakdown=dict(lead_sources_breakdown),
            leads_by_industry=dict(leads_by_industry),
            interest_by_platform=formatted_interest_by_platform,
        )

        return UriResponse.get_single_data_response("leads analytics", lead_analytics)

    @staticmethod
    async def check_for_existing_lead(
        db: AsyncIOMotorDatabase, user_id: str, lead_link: str, lead_source
    ):
        query = {
            "assigned_to": user_id,
            "lead_source": lead_source,
            "lead_link": lead_link,
        }
        existing_lead = await db["leads"].find_one(query)
        return existing_lead is None
