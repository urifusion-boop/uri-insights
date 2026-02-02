"""
Auto Dead Lead Detection Service

Automatically detects leads that should be marked as DEAD
and optionally adds them to Lazarus monitoring based on user-defined rules.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.LeadRepository import LeadRepository
from app.services.LazarusService import LazarusService
from app.domain.schemas.lazarus_schema import FocusContactCreate, CompanyMonitorCreate
from app.domain.enums.lead_enum import LeadStatusEnum


class AutoDeadLeadDetectionService:
    """Service for automatically detecting and marking dead leads"""

    @staticmethod
    async def scan_for_dead_leads(
        db: AsyncIOMotorDatabase,
        user_id: str,
        detection_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Scan user's leads and auto-mark as DEAD based on detection rules

        Args:
            db: Database connection
            user_id: User ID to scan leads for
            detection_rules: Rules for detecting dead leads
                - no_response_days: Mark dead if no activity in X days
                - status_unchanged_days: Mark dead if status hasn't changed in X days
                - min_contact_attempts: Require X contact attempts before marking dead
                - exclude_statuses: Don't auto-mark if lead is in these statuses
                - auto_add_to_lazarus: Automatically add to Lazarus monitoring
                - monitor_type: "focus_contact" or "company_monitor"

        Returns:
            Dict with scan results
        """
        # Build query to find candidate leads
        query = {
            "user_id": user_id,
            "lead_status": {"$nin": [
                LeadStatusEnum.DEAD,
                LeadStatusEnum.CONVERTED,
                LeadStatusEnum.RESURRECTED
            ]},
        }

        # Exclude specific statuses if configured
        exclude_statuses = detection_rules.get("exclude_statuses", [])
        if exclude_statuses:
            query["lead_status"]["$nin"].extend(exclude_statuses)

        # Filter by no_response_days (last activity date)
        no_response_days = detection_rules.get("no_response_days", 30)
        cutoff_date = datetime.utcnow() - timedelta(days=no_response_days)
        query["last_updated"] = {"$lt": cutoff_date}

        # Find candidate leads
        leads_collection = db["leads"]
        candidates = await leads_collection.find(query).to_list(None)

        marked_count = 0
        added_to_lazarus_count = 0
        errors = []

        for lead_doc in candidates:
            lead_id = lead_doc.get("lead_id")

            # Check minimum contact attempts if required
            min_contact_attempts = detection_rules.get("min_contact_attempts", 0)
            if min_contact_attempts > 0:
                contact_count = 0
                if lead_doc.get("emailed"):
                    contact_count += 1
                if lead_doc.get("called"):
                    contact_count += 1
                comm_history = lead_doc.get("communication_history", [])
                if isinstance(comm_history, list):
                    contact_count += len(comm_history)

                if contact_count < min_contact_attempts:
                    continue  # Skip this lead - not enough contact attempts

            # Generate auto-detection reason
            reason = f"Auto-detected: No activity for {no_response_days} days"

            # Should we auto-add to Lazarus?
            auto_monitor = detection_rules.get("auto_add_to_lazarus", False)

            try:
                # Mark lead as dead
                result = await LazarusService.mark_lead_as_dead(
                    db, user_id, lead_id, reason, auto_monitor
                )

                if result.get("success"):
                    marked_count += 1
                    if result.get("monitoring_added"):
                        added_to_lazarus_count += 1
                else:
                    errors.append({
                        "lead_id": lead_id,
                        "error": result.get("message", "Unknown error")
                    })
            except Exception as e:
                errors.append({
                    "lead_id": lead_id,
                    "error": str(e)
                })

        return {
            "scanned_leads": len(candidates),
            "marked_dead": marked_count,
            "added_to_lazarus": added_to_lazarus_count,
            "errors": errors,
            "timestamp": datetime.utcnow()
        }

    @staticmethod
    async def get_user_detection_rules(
        db: AsyncIOMotorDatabase,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's auto-detection rules from database

        Returns:
            Detection rules dict or None if not configured
        """
        rules_collection = db["dead_lead_detection_rules"]
        rules_doc = await rules_collection.find_one({"user_id": user_id})

        if not rules_doc:
            # Return default rules if none exist
            return {
                "user_id": user_id,
                "enabled": False,
                "detection_rules": {
                    "no_response_days": 30,
                    "status_unchanged_days": 60,
                    "min_contact_attempts": 2,
                    "exclude_statuses": ["Qualified", "Converted"],
                    "auto_add_to_lazarus": False,
                    "monitor_type": "focus_contact"
                },
                "schedule": "weekly",
                "last_scan_date": None,
                "next_scan_date": None,
                "created_date": datetime.utcnow(),
                "last_updated": datetime.utcnow()
            }

        return rules_doc

    @staticmethod
    async def update_user_detection_rules(
        db: AsyncIOMotorDatabase,
        user_id: str,
        rules_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user's auto-detection rules

        Args:
            db: Database connection
            user_id: User ID
            rules_update: Updated rules

        Returns:
            Updated rules document
        """
        rules_collection = db["dead_lead_detection_rules"]

        # Calculate next scan date based on schedule
        schedule = rules_update.get("schedule", "weekly")
        if schedule == "daily":
            next_scan = datetime.utcnow() + timedelta(days=1)
        elif schedule == "weekly":
            next_scan = datetime.utcnow() + timedelta(weeks=1)
        else:  # monthly
            next_scan = datetime.utcnow() + timedelta(days=30)

        # Prepare update document
        update_doc = {
            "user_id": user_id,
            "enabled": rules_update.get("enabled", False),
            "detection_rules": rules_update.get("detection_rules", {}),
            "schedule": schedule,
            "next_scan_date": next_scan,
            "last_updated": datetime.utcnow()
        }

        # Upsert (create if doesn't exist)
        result = await rules_collection.update_one(
            {"user_id": user_id},
            {
                "$set": update_doc,
                "$setOnInsert": {"created_date": datetime.utcnow()}
            },
            upsert=True
        )

        # Fetch and return updated document
        updated_doc = await rules_collection.find_one({"user_id": user_id})
        return updated_doc

    @staticmethod
    async def get_scan_history(
        db: AsyncIOMotorDatabase,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user's auto-detection scan history

        Returns:
            List of scan history records
        """
        history_collection = db["dead_lead_scan_history"]

        history = await history_collection.find(
            {"user_id": user_id}
        ).sort("scan_date", -1).skip(skip).limit(limit).to_list(None)

        return history

    @staticmethod
    async def save_scan_result(
        db: AsyncIOMotorDatabase,
        user_id: str,
        scan_result: Dict[str, Any]
    ):
        """Save scan result to history"""
        history_collection = db["dead_lead_scan_history"]

        history_doc = {
            "user_id": user_id,
            "scan_date": scan_result["timestamp"],
            "scanned_leads": scan_result["scanned_leads"],
            "marked_dead": scan_result["marked_dead"],
            "added_to_lazarus": scan_result["added_to_lazarus"],
            "errors": scan_result.get("errors", [])
        }

        await history_collection.insert_one(history_doc)
