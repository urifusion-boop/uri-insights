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

            # Scan History indexes
            await db["scan_history"].create_index([("user_id", 1)])
            await db["scan_history"].create_index([("source_id", 1)])
            await db["scan_history"].create_index([("scan_date", -1)])  # Latest first
            await db["scan_history"].create_index([("signal_detected", 1)])
            await db["scan_history"].create_index([("alert_id", 1)])

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
        if contact:
            # Fix legacy data: convert dict languages to strings
            if "languages" in contact and isinstance(contact["languages"], list):
                fixed_languages = []
                for lang in contact["languages"]:
                    if isinstance(lang, dict):
                        lang_name = lang.get("title") or lang.get("name") or lang.get("language")
                        if lang_name:
                            fixed_languages.append(lang_name)
                    elif isinstance(lang, str):
                        fixed_languages.append(lang)
                contact["languages"] = fixed_languages

            return FocusContact(**contact)
        return None

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
            # Fix legacy data: convert dict languages to strings
            if "languages" in doc and isinstance(doc["languages"], list):
                fixed_languages = []
                for lang in doc["languages"]:
                    if isinstance(lang, dict):
                        lang_name = lang.get("title") or lang.get("name") or lang.get("language")
                        if lang_name:
                            fixed_languages.append(lang_name)
                    elif isinstance(lang, str):
                        fixed_languages.append(lang)
                doc["languages"] = fixed_languages

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
            .sort("created_at", -1)
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
        acted_alerts = await db["lazarus_alerts"].count_documents(
            {"user_id": user_id, "status": LazarusAlertStatusEnum.ACTED}
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

        # Calculate utilization percentage
        utilization_percent = (slots.used_slots / slots.max_slots * 100) if slots.max_slots > 0 else 0

        # Calculate resurrection rate (% of alerts acted upon)
        total_actionable_alerts = new_alerts + acted_alerts + dismissed_alerts
        resurrection_rate = (acted_alerts / total_actionable_alerts * 100) if total_actionable_alerts > 0 else 0.0

        # Upgrade recommendations (if using >80% of slots)
        should_upgrade = utilization_percent > 80
        upgrade_from = slots.plan_type
        upgrade_to = "PRO" if slots.plan_type == "BASIC" else "ENTERPRISE"

        return {
            "used_slots": slots.used_slots,
            "max_slots": slots.max_slots,
            "utilization_percent": round(utilization_percent, 2),
            "active_focus_contacts": active_focus,
            "active_company_monitors": active_companies,
            "total_alerts": new_alerts + acted_alerts + dismissed_alerts,
            "new_alerts": new_alerts,
            "resurrected_leads": acted_alerts,  # Acted alerts = resurrected leads
            "resurrection_rate": round(resurrection_rate, 2),
            "should_upgrade": should_upgrade,
            "upgrade_from": upgrade_from,
            "upgrade_to": upgrade_to,
        }

    @staticmethod
    async def get_analytics_data(db: AsyncIOMotorDatabase, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get detailed analytics data for PRD Section 7 - Success Metrics

        Returns:
        - Resurrection rate (% of alerts acted upon)
        - Quota utilization (% of slots used)
        - Alert performance by type
        - Weekly trend data
        - False positive rate (dismissals)
        """
        from datetime import datetime, timedelta

        # Get current metrics
        slots = await LazarusRepository.get_or_create_slots(db, user_id)

        # Date range for analytics
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get all alerts in date range
        alerts_collection = db["lazarus_alerts"]
        all_alerts = await alerts_collection.find({
            "user_id": user_id,
            "created_at": {"$gte": start_date}
        }).to_list(None)

        # Calculate resurrection rate (PRD 7.1: % of alerts acted upon)
        total_alerts = len(all_alerts)
        acted_upon = len([a for a in all_alerts if a.get("status") == LazarusAlertStatusEnum.ACTED])
        dismissed = len([a for a in all_alerts if a.get("status") == LazarusAlertStatusEnum.DISMISSED])
        pending = len([a for a in all_alerts if a.get("status") == LazarusAlertStatusEnum.NEW])

        resurrection_rate = (acted_upon / total_alerts * 100) if total_alerts > 0 else 0.0

        # Calculate false positive rate (PRD 7.4: % dismissed)
        false_positive_rate = (dismissed / total_alerts * 100) if total_alerts > 0 else 0.0
        accuracy_rate = 100.0 - false_positive_rate

        # Quota utilization (PRD 7.2)
        quota_utilization = (slots.used_slots / slots.max_slots * 100) if slots.max_slots > 0 else 0.0

        # Alert performance by type
        alert_types_stats = {}
        for alert in all_alerts:
            alert_type = alert.get("alert_type", "Unknown")
            if alert_type not in alert_types_stats:
                alert_types_stats[alert_type] = {
                    "total": 0,
                    "acted_upon": 0,
                    "dismissed": 0,
                    "pending": 0
                }

            alert_types_stats[alert_type]["total"] += 1
            status = alert.get("status")
            if status == LazarusAlertStatusEnum.ACTED:
                alert_types_stats[alert_type]["acted_upon"] += 1
            elif status == LazarusAlertStatusEnum.DISMISSED:
                alert_types_stats[alert_type]["dismissed"] += 1
            elif status == LazarusAlertStatusEnum.NEW:
                alert_types_stats[alert_type]["pending"] += 1

        # Calculate action rate for each type
        for alert_type, stats in alert_types_stats.items():
            stats["action_rate"] = (stats["acted_upon"] / stats["total"] * 100) if stats["total"] > 0 else 0.0

        # Weekly trend data (last 4 weeks)
        weekly_trends = []
        for week in range(4):
            week_start = datetime.utcnow() - timedelta(days=(week + 1) * 7)
            week_end = datetime.utcnow() - timedelta(days=week * 7)

            week_alerts = [a for a in all_alerts
                          if week_start <= a.get("created_at", datetime.utcnow()) < week_end]
            week_total = len(week_alerts)
            week_acted = len([a for a in week_alerts if a.get("status") in [
                LazarusAlertStatusEnum.CONTACTED, LazarusAlertStatusEnum.RESURRECTED
            ]])

            week_rate = (week_acted / week_total * 100) if week_total > 0 else 0.0

            weekly_trends.insert(0, {  # Insert at beginning to get chronological order
                "week": f"Week {4 - week}",
                "start_date": week_start.isoformat(),
                "end_date": week_end.isoformat(),
                "resurrection_rate": round(week_rate, 1),
                "total_alerts": week_total,
                "acted_upon": week_acted
            })

        # Get resurrected leads count
        leads_collection = db["leads"]
        resurrected_leads = await leads_collection.count_documents({
            "user_id": user_id,
            "status": "RESURRECTED",
            "last_resurrection_date": {"$gte": start_date}
        })

        # Calculate real funnel metrics (for AdvancedAnalytics component)
        # Get focus contacts and company monitors
        focus_contacts = await db["focus_contacts"].count_documents({
            "user_id": user_id,
            "monitoring_status": "ACTIVE"
        })
        company_monitors = await db["company_monitors"].count_documents({
            "user_id": user_id,
            "monitoring_status": "ACTIVE"
        })
        contacts_monitored = focus_contacts + company_monitors

        # Count scans completed in date range (actual scan attempts)
        scans_completed = await db["focus_contacts"].count_documents({
            "user_id": user_id,
            "last_scan_date": {"$gte": start_date}
        }) + await db["company_monitors"].count_documents({
            "user_id": user_id,
            "last_scan_date": {"$gte": start_date}
        })

        # Platform performance (count alerts by platform)
        linkedin_alerts = len([a for a in all_alerts if a.get("evidence", {}).get("post_platform") == "LinkedIn"])
        twitter_alerts = len([a for a in all_alerts if a.get("evidence", {}).get("post_platform") == "Twitter"])
        facebook_alerts = len([a for a in all_alerts if a.get("evidence", {}).get("post_platform") == "Facebook"])
        tiktok_alerts = len([a for a in all_alerts if a.get("evidence", {}).get("post_platform") == "TikTok"])

        return {
            # KPI Metrics
            "resurrection_rate": round(resurrection_rate, 1),
            "resurrection_rate_target": 15.0,  # PRD 7.1: Goal >15%
            "resurrection_rate_status": "above_target" if resurrection_rate >= 15.0 else "below_target",

            "quota_utilization": round(quota_utilization, 1),
            "slots_used": slots.used_slots,
            "slots_total": slots.max_slots,
            "slots_remaining": slots.max_slots - slots.used_slots,

            "accuracy_rate": round(accuracy_rate, 1),
            "false_positive_rate": round(false_positive_rate, 1),

            # Alert Performance
            "total_alerts": total_alerts,
            "acted_upon_count": acted_upon,
            "dismissed_count": dismissed,
            "pending_count": pending,
            "resurrected_leads_count": resurrected_leads,

            # Breakdown percentages
            "contacted_percentage": round((acted_upon / total_alerts * 100) if total_alerts > 0 else 0, 1),
            "dismissed_percentage": round((dismissed / total_alerts * 100) if total_alerts > 0 else 0, 1),
            "pending_percentage": round((pending / total_alerts * 100) if total_alerts > 0 else 0, 1),

            # Alert type performance
            "alert_types_performance": sorted(
                [
                    {
                        "alert_type": alert_type,
                        **stats
                    }
                    for alert_type, stats in alert_types_stats.items()
                ],
                key=lambda x: x["action_rate"],
                reverse=True
            ),

            # Trend data
            "weekly_trends": weekly_trends,

            # Plan info
            "plan_type": slots.plan_type,
            "should_upgrade": quota_utilization >= 90.0 and slots.plan_type == "BASIC",

            # Phase 3: Real funnel metrics for AdvancedAnalytics component
            "funnel_metrics": {
                "contacts_monitored": contacts_monitored,
                "scans_completed": scans_completed,
                "alerts_created": total_alerts,
                "contacts_reached": acted_upon,
                "deals_resurrected": resurrected_leads,
            },

            # Platform performance breakdown
            "platform_breakdown": {
                "LinkedIn": linkedin_alerts,
                "Twitter": twitter_alerts,
                "Facebook": facebook_alerts,
                "TikTok": tiktok_alerts,
            }
        }

    # ============ HELPER METHODS FOR CRM SYNC ============
    @staticmethod
    async def get_focus_contact_by_email(
        db: AsyncIOMotorDatabase,
        user_id: str,
        email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get focus contact by email address (for duplicate detection during CRM sync)

        Args:
            db: Database connection
            user_id: User ID
            email: Email address

        Returns:
            Focus contact or None if not found
        """
        try:
            contact = await db["focus_contacts"].find_one({
                "user_id": user_id,
                "email": email
            })

            if contact:
                contact["_id"] = str(contact["_id"])
                return contact

            return None

        except Exception as e:
            print(f"Error getting focus contact by email: {str(e)}")
            return None

    @staticmethod
    async def get_company_monitor_by_name(
        db: AsyncIOMotorDatabase,
        user_id: str,
        company_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get company monitor by company name (for duplicate detection during CRM sync)

        Args:
            db: Database connection
            user_id: User ID
            company_name: Company name

        Returns:
            Company monitor or None if not found
        """
        try:
            # Case-insensitive search
            monitor = await db["company_monitors"].find_one({
                "user_id": user_id,
                "company_name": {"$regex": f"^{company_name}$", "$options": "i"}
            })

            if monitor:
                monitor["_id"] = str(monitor["_id"])
                return monitor

            return None

        except Exception as e:
            print(f"Error getting company monitor by name: {str(e)}")
            return None

    @staticmethod
    async def get_alert_by_id(
        db: AsyncIOMotorDatabase,
        user_id: str,
        alert_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get Lazarus alert by ID (for syncing back to CRM)

        Args:
            db: Database connection
            user_id: User ID
            alert_id: Alert ID

        Returns:
            Alert document or None if not found
        """
        try:
            alert = await db["lazarus_alerts"].find_one({
                "alert_id": alert_id,
                "user_id": user_id
            })

            if alert:
                alert["_id"] = str(alert["_id"])
                return alert

            return None

        except Exception as e:
            print(f"Error getting alert by ID: {str(e)}")
            return None
