from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import pymongo
import pymongo.errors

from app.domain.schemas.lazarus_schema import (
    FocusContact,
    CompanyMonitor,
    LazarusAlert,
    LazarusSlots,
    LazarusMonitorTypeEnum,
    LazarusMonitoringStatusEnum,
    LazarusAlertStatusEnum,
    LazarusPlanTypeEnum,
)


class LazarusRepository:
    """Repository for Lazarus Protocol database operations"""

    # ============ INDEXES ============
    @staticmethod
    async def setup_indexes(db: AsyncIOMotorDatabase):
        """Setup indexes for all Lazarus collections"""
        try:
            print("⚙️ Setting up indexes for Lazarus Protocol collections...")

            # Focus Contacts indexes
            await db["focus_contacts"].create_index([("user_id", 1)])
            await db["focus_contacts"].create_index([("monitoring_status", 1)])
            await db["focus_contacts"].create_index([("next_scan_date", 1)])
            await db["focus_contacts"].create_index(
                [("user_id", 1), ("social_handle", 1)], unique=True, sparse=True
            )  # Prevent duplicate handles per user
            await db["focus_contacts"].create_index([("source_lead_id", 1)])

            # Company Monitors indexes
            await db["company_monitors"].create_index([("user_id", 1)])
            await db["company_monitors"].create_index([("monitoring_status", 1)])
            await db["company_monitors"].create_index([("next_scan_date", 1)])
            await db["company_monitors"].create_index(
                [("user_id", 1), ("website_url", 1)], unique=True, sparse=True
            )  # Prevent duplicate companies per user
            await db["company_monitors"].create_index([("source_lead_id", 1)])

            # Lazarus Alerts indexes
            await db["lazarus_alerts"].create_index([("user_id", 1)])
            await db["lazarus_alerts"].create_index([("status", 1)])
            await db["lazarus_alerts"].create_index([("alert_type", 1)])
            await db["lazarus_alerts"].create_index([("source_type", 1)])
            await db["lazarus_alerts"].create_index([("source_id", 1)])
            await db["lazarus_alerts"].create_index([("created_date", -1)])  # Latest first

            # Lazarus Slots indexes
            await db["lazarus_slots"].create_index([("user_id", 1)], unique=True)

            print("✅ Lazarus Protocol indexes created successfully")
        except pymongo.errors.PyMongoError as e:
            print(f"❌ Error creating Lazarus indexes: {str(e)}")

    # ============ FOCUS CONTACTS ============
    @staticmethod
    async def create_focus_contact(
        db: AsyncIOMotorDatabase, contact_data: Dict[str, Any]
    ) -> Optional[FocusContact]:
        """Create a new focus contact"""
        try:
            result = await db["focus_contacts"].insert_one(contact_data)
            contact_data["_id"] = str(result.inserted_id)
            return FocusContact(**contact_data)
        except pymongo.errors.DuplicateKeyError:
            return None
        except Exception as e:
            print(f"❌ Error creating focus contact: {str(e)}")
            return None

    @staticmethod
    async def get_focus_contact_by_id(
        db: AsyncIOMotorDatabase, focus_id: str, user_id: str
    ) -> Optional[FocusContact]:
        """Get focus contact by ID"""
        contact = await db["focus_contacts"].find_one(
            {"focus_id": focus_id, "user_id": user_id}
        )
        return FocusContact(**contact) if contact else None

    @staticmethod
    async def get_focus_contacts_by_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        status: Optional[LazarusMonitoringStatusEnum] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[FocusContact]:
        """Get all focus contacts for a user"""
        query = {"user_id": user_id}
        if status:
            query["monitoring_status"] = status

        cursor = (
            db["focus_contacts"]
            .find(query)
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
        )

        contacts = []
        async for doc in cursor:
            contacts.append(FocusContact(**doc))
        return contacts

    @staticmethod
    async def get_contacts_for_scan(
        db: AsyncIOMotorDatabase, batch_size: int = 100
    ) -> List[FocusContact]:
        """Get focus contacts due for scanning (next_scan_date <= now)"""
        now = datetime.utcnow()
        cursor = (
            db["focus_contacts"]
            .find(
                {
                    "monitoring_status": LazarusMonitoringStatusEnum.ACTIVE,
                    "next_scan_date": {"$lte": now},
                }
            )
            .limit(batch_size)
        )

        contacts = []
        async for doc in cursor:
            contacts.append(FocusContact(**doc))
        return contacts

    @staticmethod
    async def update_focus_contact(
        db: AsyncIOMotorDatabase, focus_id: str, user_id: str, update_data: Dict[str, Any]
    ) -> Optional[FocusContact]:
        """Update focus contact"""
        update_data["last_updated"] = datetime.utcnow()
        result = await db["focus_contacts"].find_one_and_update(
            {"focus_id": focus_id, "user_id": user_id},
            {"$set": update_data},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return FocusContact(**result) if result else None

    @staticmethod
    async def delete_focus_contact(
        db: AsyncIOMotorDatabase, focus_id: str, user_id: str
    ) -> bool:
        """Delete focus contact"""
        result = await db["focus_contacts"].delete_one(
            {"focus_id": focus_id, "user_id": user_id}
        )
        return result.deleted_count > 0

    @staticmethod
    async def count_focus_contacts_by_user(
        db: AsyncIOMotorDatabase, user_id: str
    ) -> int:
        """Count total focus contacts for a user"""
        return await db["focus_contacts"].count_documents({"user_id": user_id})

    # ============ COMPANY MONITORS ============
    @staticmethod
    async def create_company_monitor(
        db: AsyncIOMotorDatabase, monitor_data: Dict[str, Any]
    ) -> Optional[CompanyMonitor]:
        """Create a new company monitor"""
        try:
            result = await db["company_monitors"].insert_one(monitor_data)
            monitor_data["_id"] = str(result.inserted_id)
            return CompanyMonitor(**monitor_data)
        except pymongo.errors.DuplicateKeyError:
            return None
        except Exception as e:
            print(f"❌ Error creating company monitor: {str(e)}")
            return None

    @staticmethod
    async def get_company_monitor_by_id(
        db: AsyncIOMotorDatabase, monitor_id: str, user_id: str
    ) -> Optional[CompanyMonitor]:
        """Get company monitor by ID"""
        monitor = await db["company_monitors"].find_one(
            {"monitor_id": monitor_id, "user_id": user_id}
        )
        return CompanyMonitor(**monitor) if monitor else None

    @staticmethod
    async def get_company_monitors_by_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        status: Optional[LazarusMonitoringStatusEnum] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[CompanyMonitor]:
        """Get all company monitors for a user"""
        query = {"user_id": user_id}
        if status:
            query["monitoring_status"] = status

        cursor = (
            db["company_monitors"]
            .find(query)
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
        )

        monitors = []
        async for doc in cursor:
            monitors.append(CompanyMonitor(**doc))
        return monitors

    @staticmethod
    async def get_monitors_for_scan(
        db: AsyncIOMotorDatabase, batch_size: int = 100
    ) -> List[CompanyMonitor]:
        """Get company monitors due for scanning"""
        now = datetime.utcnow()
        cursor = (
            db["company_monitors"]
            .find(
                {
                    "monitoring_status": LazarusMonitoringStatusEnum.ACTIVE,
                    "next_scan_date": {"$lte": now},
                }
            )
            .limit(batch_size)
        )

        monitors = []
        async for doc in cursor:
            monitors.append(CompanyMonitor(**doc))
        return monitors

    @staticmethod
    async def update_company_monitor(
        db: AsyncIOMotorDatabase,
        monitor_id: str,
        user_id: str,
        update_data: Dict[str, Any],
    ) -> Optional[CompanyMonitor]:
        """Update company monitor"""
        update_data["last_updated"] = datetime.utcnow()
        result = await db["company_monitors"].find_one_and_update(
            {"monitor_id": monitor_id, "user_id": user_id},
            {"$set": update_data},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return CompanyMonitor(**result) if result else None

    @staticmethod
    async def delete_company_monitor(
        db: AsyncIOMotorDatabase, monitor_id: str, user_id: str
    ) -> bool:
        """Delete company monitor"""
        result = await db["company_monitors"].delete_one(
            {"monitor_id": monitor_id, "user_id": user_id}
        )
        return result.deleted_count > 0

    @staticmethod
    async def count_company_monitors_by_user(
        db: AsyncIOMotorDatabase, user_id: str
    ) -> int:
        """Count total company monitors for a user"""
        return await db["company_monitors"].count_documents({"user_id": user_id})

    # ============ LAZARUS ALERTS ============
    @staticmethod
    async def create_alert(
        db: AsyncIOMotorDatabase, alert_data: Dict[str, Any]
    ) -> Optional[LazarusAlert]:
        """Create a new Lazarus alert"""
        try:
            result = await db["lazarus_alerts"].insert_one(alert_data)
            alert_data["_id"] = str(result.inserted_id)
            return LazarusAlert(**alert_data)
        except Exception as e:
            print(f"❌ Error creating Lazarus alert: {str(e)}")
            return None

    @staticmethod
    async def get_alerts_by_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        status: Optional[LazarusAlertStatusEnum] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[LazarusAlert]:
        """Get alerts for a user"""
        query = {"user_id": user_id}
        if status:
            query["status"] = status

        cursor = (
            db["lazarus_alerts"]
            .find(query)
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
        )

        alerts = []
        async for doc in cursor:
            alerts.append(LazarusAlert(**doc))
        return alerts

    @staticmethod
    async def update_alert_status(
        db: AsyncIOMotorDatabase,
        alert_id: str,
        user_id: str,
        status: LazarusAlertStatusEnum,
    ) -> Optional[LazarusAlert]:
        """Update alert status"""
        result = await db["lazarus_alerts"].find_one_and_update(
            {"alert_id": alert_id, "user_id": user_id},
            {"$set": {"status": status, "last_updated": datetime.utcnow()}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return LazarusAlert(**result) if result else None

    @staticmethod
    async def count_alerts_by_user(
        db: AsyncIOMotorDatabase, user_id: str, status: Optional[LazarusAlertStatusEnum] = None
    ) -> int:
        """Count alerts for a user"""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        return await db["lazarus_alerts"].count_documents(query)

    # ============ LAZARUS SLOTS ============
    @staticmethod
    async def get_or_create_slots(
        db: AsyncIOMotorDatabase, user_id: str
    ) -> LazarusSlots:
        """Get or create slots for a user (defaults to BASIC plan)"""
        slots = await db["lazarus_slots"].find_one({"user_id": user_id})

        if not slots:
            # Create default BASIC plan with 50 slots
            slots_data = {
                "user_id": user_id,
                "plan_type": LazarusPlanTypeEnum.BASIC,
                "max_slots": 50,
                "used_slots": 0,
                "focus_contacts_count": 0,
                "company_monitors_count": 0,
                "created_date": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
            }
            await db["lazarus_slots"].insert_one(slots_data)
            return LazarusSlots(**slots_data)

        return LazarusSlots(**slots)

    @staticmethod
    async def update_slots(
        db: AsyncIOMotorDatabase, user_id: str, update_data: Dict[str, Any]
    ) -> Optional[LazarusSlots]:
        """Update user slots"""
        update_data["last_updated"] = datetime.utcnow()
        result = await db["lazarus_slots"].find_one_and_update(
            {"user_id": user_id},
            {"$set": update_data},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return LazarusSlots(**result) if result else None

    @staticmethod
    async def increment_slot_usage(
        db: AsyncIOMotorDatabase, user_id: str, contact_type: LazarusMonitorTypeEnum
    ) -> bool:
        """Increment slot usage when adding a new monitor"""
        increment_field = (
            "focus_contacts_count"
            if contact_type == LazarusMonitorTypeEnum.FOCUS_CONTACT
            else "company_monitors_count"
        )

        result = await db["lazarus_slots"].update_one(
            {"user_id": user_id},
            {
                "$inc": {"used_slots": 1, increment_field: 1},
                "$set": {"last_updated": datetime.utcnow()},
            },
        )
        return result.modified_count > 0

    @staticmethod
    async def decrement_slot_usage(
        db: AsyncIOMotorDatabase, user_id: str, contact_type: LazarusMonitorTypeEnum
    ) -> bool:
        """Decrement slot usage when removing a monitor"""
        decrement_field = (
            "focus_contacts_count"
            if contact_type == LazarusMonitorTypeEnum.FOCUS_CONTACT
            else "company_monitors_count"
        )

        result = await db["lazarus_slots"].update_one(
            {"user_id": user_id},
            {
                "$inc": {"used_slots": -1, decrement_field: -1},
                "$set": {"last_updated": datetime.utcnow()},
            },
        )
        return result.modified_count > 0

    @staticmethod
    async def upgrade_plan(
        db: AsyncIOMotorDatabase, user_id: str, new_plan: LazarusPlanTypeEnum
    ) -> Optional[LazarusSlots]:
        """Upgrade user's plan (BASIC 50 -> PRO 500)"""
        max_slots = 50 if new_plan == LazarusPlanTypeEnum.BASIC else 500

        result = await db["lazarus_slots"].find_one_and_update(
            {"user_id": user_id},
            {
                "$set": {
                    "plan_type": new_plan,
                    "max_slots": max_slots,
                    "last_updated": datetime.utcnow(),
                }
            },
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return LazarusSlots(**result) if result else None

    # ============ METRICS & ANALYTICS ============
    @staticmethod
    async def get_user_metrics(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
        """Get Lazarus metrics for a user"""
        slots = await LazarusRepository.get_or_create_slots(db, user_id)

        # Count alerts by status
        new_alerts = await db["lazarus_alerts"].count_documents(
            {"user_id": user_id, "status": LazarusAlertStatusEnum.NEW}
        )
        contacted_alerts = await db["lazarus_alerts"].count_documents(
            {"user_id": user_id, "status": LazarusAlertStatusEnum.CONTACTED}
        )
        dismissed_alerts = await db["lazarus_alerts"].count_documents(
            {"user_id": user_id, "status": LazarusAlertStatusEnum.DISMISSED}
        )

        # Get active monitors count
        active_focus = await db["focus_contacts"].count_documents(
            {"user_id": user_id, "monitoring_status": LazarusMonitoringStatusEnum.ACTIVE}
        )
        active_companies = await db["company_monitors"].count_documents(
            {"user_id": user_id, "monitoring_status": LazarusMonitoringStatusEnum.ACTIVE}
        )

        return {
            "slots_used": slots.used_slots,
            "slots_available": slots.max_slots - slots.used_slots,
            "max_slots": slots.max_slots,
            "plan_type": slots.plan_type,
            "focus_contacts_count": slots.focus_contacts_count,
            "company_monitors_count": slots.company_monitors_count,
            "active_focus_contacts": active_focus,
            "active_company_monitors": active_companies,
            "new_alerts_count": new_alerts,
            "contacted_alerts_count": contacted_alerts,
            "dismissed_alerts_count": dismissed_alerts,
            "total_alerts": new_alerts + contacted_alerts + dismissed_alerts,
        }
