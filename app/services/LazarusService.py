import hashlib
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.LazarusRepository import LazarusRepository
from app.repository.LeadRepository import LeadRepository
from app.core.helpers.social_url_helper import SocialURLHelper
from app.domain.schemas.lazarus_schema import (
    FocusContact,
    FocusContactCreate,
    CompanyMonitor,
    CompanyMonitorCreate,
    LazarusAlert,
    LazarusSlots,
    LazarusMonitorTypeEnum,
    LazarusMonitoringStatusEnum,
    LazarusAlertTypeEnum,
    LazarusAlertStatusEnum,
    LazarusPlanTypeEnum,
    CSVUploadRow,
    LazarusMetrics,
)
from app.domain.enums.lead_enum import LeadStatusEnum, LeadSourceEnum


class LazarusService:
    """Service for Lazarus Protocol - CRM Resurrection Engine"""

    # ============ FOCUS CONTACTS ============
    @staticmethod
    async def add_focus_contact(
        db: AsyncIOMotorDatabase,
        user_id: str,
        contact_create: FocusContactCreate,
        source_lead_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a new focus contact to monitor
        PRD Section 4.1: Focus Contact Monitoring
        """
        # Check if user has available slots
        slots = await LazarusRepository.get_or_create_slots(db, user_id)
        if slots.used_slots >= slots.max_slots:
            return {
                "success": False,
                "message": f"Slot limit reached. You have {slots.max_slots} slots on the {slots.plan_type} plan.",
                "slots_available": 0,
            }

        # Create MD5 hash of bio if provided
        last_bio_hash = None
        if contact_create.last_bio_text:
            last_bio_hash = hashlib.md5(
                contact_create.last_bio_text.encode()
            ).hexdigest()

        # Use custom scan frequency or default to 7 days
        scan_frequency = contact_create.scan_frequency_days or 7

        # Parse social_handle to detect LinkedIn/Twitter URLs intelligently
        # If explicit linkedin_url or twitter_url provided, use those
        # Otherwise, parse social_handle to extract them
        linkedin_url = contact_create.linkedin_url
        twitter_url = contact_create.twitter_url

        if not linkedin_url and not twitter_url and contact_create.social_handle:
            # Parse social_handle to detect which platform it is
            parsed_urls = SocialURLHelper.parse_social_handle(contact_create.social_handle)
            linkedin_url = parsed_urls.get("linkedin_url")
            twitter_url = parsed_urls.get("twitter_url")

            # Log the intelligent detection
            detected_platform = "LinkedIn" if linkedin_url else "Twitter" if twitter_url else "Unknown"
            print(f"[LAZARUS] Intelligent URL Detection:")
            print(f"  Input: {contact_create.social_handle}")
            print(f"  Detected Platform: {detected_platform}")
            print(f"  LinkedIn URL: {linkedin_url}")
            print(f"  Twitter URL: {twitter_url}")

        # Build focus contact data
        contact_data = {
            "focus_id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": contact_create.name,
            "social_handle": contact_create.social_handle,
            "linkedin_url": linkedin_url,
            "twitter_url": twitter_url,
            "current_company": contact_create.current_company,
            "last_bio_text": contact_create.last_bio_text,
            "last_bio_hash": last_bio_hash,
            "industry_keywords": contact_create.industry_keywords,
            "monitoring_status": LazarusMonitoringStatusEnum.ACTIVE,
            "source_lead_id": source_lead_id,
            "last_scan_date": None,
            "next_scan_date": datetime.utcnow() + timedelta(days=scan_frequency),
            "scan_frequency_days": scan_frequency,
            "scan_count": 0,
            "alert_count": 0,
            "created_date": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
        }

        # Create in database
        contact = await LazarusRepository.create_focus_contact(db, contact_data)
        if not contact:
            return {
                "success": False,
                "message": "Failed to create focus contact. Possibly duplicate.",
            }

        # Increment slot usage
        await LazarusRepository.increment_slot_usage(
            db, user_id, LazarusMonitorTypeEnum.FOCUS_CONTACT
        )

        # If linked to a lead, mark the lead as monitored
        if source_lead_id:
            await LeadRepository.update_lead(
                db,
                source_lead_id,
                user_id,
                {
                    "is_lazarus_monitored": True,
                    "lazarus_focus_id": contact_data["focus_id"],
                    "status": LeadStatusEnum.MONITORING,
                },
            )

        # Auto-trigger enrichment if LinkedIn URL is provided
        # This ensures profile photo, email, and other data are immediately available
        if linkedin_url:
            from app.services.LinkedInProfileScraperService import LinkedInProfileScraperService
            from datetime import datetime

            print(f"[LAZARUS] Auto-enriching new contact: {contact_create.name}")
            print(f"[LAZARUS] LinkedIn URL: {linkedin_url}")

            try:
                # Update status to pending
                await LazarusRepository.update_focus_contact(
                    db, contact_data["focus_id"], user_id, {"enrichment_status": "pending"}
                )

                # Call LinkedIn Profile Scraper
                scraper_service = LinkedInProfileScraperService()
                enrichment_result = await scraper_service.enrich_profile(
                    linkedin_url=linkedin_url,
                    timeout_seconds=90
                )

                if enrichment_result.get("success"):
                    profile_data = enrichment_result.get("profile", {})

                    # Update contact with enriched data
                    update_data = {
                        "profile_photo_url": profile_data.get("profile_photo_url"),
                        "email": profile_data.get("email"),
                        "phone": profile_data.get("phone"),
                        "current_company": profile_data.get("current_company") or contact_data.get("current_company"),
                        "current_title": profile_data.get("current_title"),
                        "enrichment_status": "completed",
                        "enriched_at": datetime.utcnow()
                    }

                    # Remove None values
                    update_data = {k: v for k, v in update_data.items() if v is not None}

                    await LazarusRepository.update_focus_contact(
                        db, contact_data["focus_id"], user_id, update_data
                    )

                    print(f"[LAZARUS] ✅ Auto-enrichment successful for {contact_create.name}")
                else:
                    # Mark as failed but don't block contact creation
                    await LazarusRepository.update_focus_contact(
                        db, contact_data["focus_id"], user_id, {
                            "enrichment_status": "failed",
                            "enriched_at": datetime.utcnow()
                        }
                    )
                    print(f"[LAZARUS] ⚠️  Auto-enrichment failed: {enrichment_result.get('error_message')}")

            except Exception as e:
                print(f"[LAZARUS] ⚠️  Auto-enrichment error: {str(e)}")
                # Don't fail the whole operation if enrichment fails
                import traceback
                traceback.print_exc()

        return {
            "success": True,
            "message": "Focus contact added successfully" + (" and enrichment started" if linkedin_url else ""),
            "focus_id": contact_data["focus_id"],
            "slots_used": slots.used_slots + 1,
            "slots_available": slots.max_slots - (slots.used_slots + 1),
        }

    @staticmethod
    async def remove_focus_contact(
        db: AsyncIOMotorDatabase, user_id: str, focus_id: str
    ) -> Dict[str, Any]:
        """Remove a focus contact and free up the slot"""
        # Get the contact to find linked lead
        contact = await LazarusRepository.get_focus_contact_by_id(db, focus_id, user_id)
        if not contact:
            return {"success": False, "message": "Focus contact not found"}

        # Delete the contact
        deleted = await LazarusRepository.delete_focus_contact(db, focus_id, user_id)
        if not deleted:
            return {"success": False, "message": "Failed to delete focus contact"}

        # Decrement slot usage
        await LazarusRepository.decrement_slot_usage(
            db, user_id, LazarusMonitorTypeEnum.FOCUS_CONTACT
        )

        # Unlink from lead if exists
        if contact.source_lead_id:
            await LeadRepository.update_lead(
                db,
                contact.source_lead_id,
                user_id,
                {
                    "is_lazarus_monitored": False,
                    "lazarus_focus_id": None,
                },
            )

        return {"success": True, "message": "Focus contact removed successfully"}

    @staticmethod
    async def pause_focus_contact(
        db: AsyncIOMotorDatabase, user_id: str, focus_id: str
    ) -> Dict[str, Any]:
        """Pause monitoring for a focus contact (keeps slot occupied)"""
        updated = await LazarusRepository.update_focus_contact(
            db, focus_id, user_id, {"monitoring_status": LazarusMonitoringStatusEnum.PAUSED}
        )

        if not updated:
            return {"success": False, "message": "Focus contact not found"}

        return {"success": True, "message": "Focus contact paused"}

    @staticmethod
    async def resume_focus_contact(
        db: AsyncIOMotorDatabase, user_id: str, focus_id: str
    ) -> Dict[str, Any]:
        """Resume monitoring for a paused focus contact"""
        # Get contact to retrieve scan frequency
        contact = await LazarusRepository.get_focus_contact_by_id(db, focus_id, user_id)
        if not contact:
            return {"success": False, "message": "Focus contact not found"}

        scan_frequency = contact.scan_frequency_days if hasattr(contact, 'scan_frequency_days') else 7

        updated = await LazarusRepository.update_focus_contact(
            db,
            focus_id,
            user_id,
            {
                "monitoring_status": LazarusMonitoringStatusEnum.ACTIVE,
                "next_scan_date": datetime.utcnow() + timedelta(days=scan_frequency),
            },
        )

        if not updated:
            return {"success": False, "message": "Failed to update focus contact"}

        return {"success": True, "message": "Focus contact resumed"}

    # ============ COMPANY MONITORS ============
    @staticmethod
    async def add_company_monitor(
        db: AsyncIOMotorDatabase,
        user_id: str,
        monitor_create: CompanyMonitorCreate,
        source_lead_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a new company monitor
        PRD Section 3 Track A: Company Monitoring
        """
        # Check slots
        slots = await LazarusRepository.get_or_create_slots(db, user_id)
        if slots.used_slots >= slots.max_slots:
            return {
                "success": False,
                "message": f"Slot limit reached. You have {slots.max_slots} slots on the {slots.plan_type} plan.",
                "slots_available": 0,
            }

        # Create MD5 hash of homepage if provided
        last_homepage_hash = None
        if monitor_create.last_homepage_content:
            last_homepage_hash = hashlib.md5(
                monitor_create.last_homepage_content.encode()
            ).hexdigest()

        # Use custom scan frequency or default to 7 days
        scan_frequency = monitor_create.scan_frequency_days or 7

        # Build company monitor data
        monitor_data = {
            "monitor_id": str(uuid.uuid4()),
            "user_id": user_id,
            "company_name": monitor_create.company_name,
            "website_url": monitor_create.website_url,
            "last_homepage_hash": last_homepage_hash,
            "last_job_count": monitor_create.last_job_count or 0,
            "consecutive_404_count": 0,
            "monitoring_status": LazarusMonitoringStatusEnum.ACTIVE,
            "source_lead_id": source_lead_id,
            "last_scan_date": None,
            "next_scan_date": datetime.utcnow() + timedelta(days=scan_frequency),
            "scan_frequency_days": scan_frequency,
            "scan_count": 0,
            "alert_count": 0,
            "created_date": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
        }

        # Create in database
        monitor = await LazarusRepository.create_company_monitor(db, monitor_data)
        if not monitor:
            return {
                "success": False,
                "message": "Failed to create company monitor. Possibly duplicate.",
            }

        # Increment slot usage
        await LazarusRepository.increment_slot_usage(
            db, user_id, LazarusMonitorTypeEnum.COMPANY
        )

        # If linked to a lead, mark it as monitored
        if source_lead_id:
            await LeadRepository.update_lead(
                db,
                source_lead_id,
                user_id,
                {
                    "is_lazarus_monitored": True,
                    "lazarus_company_monitor_id": monitor_data["monitor_id"],
                    "status": LeadStatusEnum.MONITORING,
                },
            )

        return {
            "success": True,
            "message": "Company monitor added successfully",
            "monitor_id": monitor_data["monitor_id"],
            "slots_used": slots.used_slots + 1,
            "slots_available": slots.max_slots - (slots.used_slots + 1),
        }

    @staticmethod
    async def remove_company_monitor(
        db: AsyncIOMotorDatabase, user_id: str, monitor_id: str
    ) -> Dict[str, Any]:
        """Remove a company monitor and free up the slot"""
        # Get the monitor to find linked lead
        monitor = await LazarusRepository.get_company_monitor_by_id(
            db, monitor_id, user_id
        )
        if not monitor:
            return {"success": False, "message": "Company monitor not found"}

        # Delete the monitor
        deleted = await LazarusRepository.delete_company_monitor(db, monitor_id, user_id)
        if not deleted:
            return {"success": False, "message": "Failed to delete company monitor"}

        # Decrement slot usage
        await LazarusRepository.decrement_slot_usage(
            db, user_id, LazarusMonitorTypeEnum.COMPANY
        )

        # Unlink from lead if exists
        if monitor.source_lead_id:
            await LeadRepository.update_lead(
                db,
                monitor.source_lead_id,
                user_id,
                {
                    "is_lazarus_monitored": False,
                    "lazarus_company_monitor_id": None,
                },
            )

        return {"success": True, "message": "Company monitor removed successfully"}

    # ============ BULK CSV UPLOAD ============
    @staticmethod
    async def bulk_upload_from_csv(
        db: AsyncIOMotorDatabase, user_id: str, csv_rows: List[CSVUploadRow]
    ) -> Dict[str, Any]:
        """
        Bulk upload focus contacts/companies from CSV
        PRD Section 4.2: Bulk Upload via CSV
        """
        slots = await LazarusRepository.get_or_create_slots(db, user_id)
        slots_available = slots.max_slots - slots.used_slots

        if len(csv_rows) > slots_available:
            return {
                "success": False,
                "message": f"Not enough slots. You need {len(csv_rows)} slots but only have {slots_available} available.",
            }

        added_count = 0
        failed_count = 0
        errors = []

        for row in csv_rows:
            try:
                if row.type == LazarusMonitorTypeEnum.FOCUS_CONTACT:
                    contact_create = FocusContactCreate(
                        name=row.name,
                        social_handle=row.social_handle,
                        last_bio_text=row.current_bio,
                        industry_keywords=row.industry_keywords or [],
                        scan_frequency_days=row.scan_frequency_days or 7,
                    )
                    result = await LazarusService.add_focus_contact(
                        db, user_id, contact_create
                    )
                else:  # COMPANY
                    monitor_create = CompanyMonitorCreate(
                        company_name=row.name,
                        website_url=row.website_url,
                        last_homepage_content=None,
                        last_job_count=0,
                        scan_frequency_days=row.scan_frequency_days or 7,
                    )
                    result = await LazarusService.add_company_monitor(
                        db, user_id, monitor_create
                    )

                if result["success"]:
                    added_count += 1
                else:
                    failed_count += 1
                    errors.append({"name": row.name, "error": result["message"]})

            except Exception as e:
                failed_count += 1
                errors.append({"name": row.name, "error": str(e)})

        return {
            "success": True,
            "message": f"Uploaded {added_count} monitors. {failed_count} failed.",
            "added_count": added_count,
            "failed_count": failed_count,
            "errors": errors,
        }

    # ============ ALERTS ============
    @staticmethod
    async def get_alerts(
        db: AsyncIOMotorDatabase,
        user_id: str,
        status: Optional[LazarusAlertStatusEnum] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[LazarusAlert]:
        """Get Lazarus alerts for a user"""
        return await LazarusRepository.get_alerts_by_user(
            db, user_id, status, skip, limit
        )

    @staticmethod
    async def mark_alert_contacted(
        db: AsyncIOMotorDatabase, user_id: str, alert_id: str
    ) -> Dict[str, Any]:
        """Mark an alert as contacted"""
        updated = await LazarusRepository.update_alert_status(
            db, alert_id, user_id, LazarusAlertStatusEnum.ACTED
        )

        if not updated:
            return {"success": False, "message": "Alert not found"}

        # If alert has linked lead, update the lead
        if updated.resurrected_lead_id:
            await LeadRepository.update_lead(
                db,
                updated.resurrected_lead_id,
                user_id,
                {
                    "status": LeadStatusEnum.CONTACTED,
                    "last_updated": datetime.utcnow(),
                },
            )

        return {"success": True, "message": "Alert marked as contacted"}

    @staticmethod
    async def dismiss_alert(
        db: AsyncIOMotorDatabase, user_id: str, alert_id: str
    ) -> Dict[str, Any]:
        """Dismiss an alert (not interested)"""
        updated = await LazarusRepository.update_alert_status(
            db, alert_id, user_id, LazarusAlertStatusEnum.DISMISSED
        )

        if not updated:
            return {"success": False, "message": "Alert not found"}

        return {"success": True, "message": "Alert dismissed"}

    # ============ SLOTS & METRICS ============
    @staticmethod
    async def get_user_slots(
        db: AsyncIOMotorDatabase, user_id: str
    ) -> LazarusSlots:
        """Get user's slot information"""
        return await LazarusRepository.get_or_create_slots(db, user_id)

    @staticmethod
    async def get_user_metrics(
        db: AsyncIOMotorDatabase, user_id: str
    ) -> LazarusMetrics:
        """Get comprehensive Lazarus metrics for a user (PRD Section 7)"""
        metrics_data = await LazarusRepository.get_user_metrics(db, user_id)
        return LazarusMetrics(**metrics_data)

    @staticmethod
    async def get_analytics_data(
        db: AsyncIOMotorDatabase, user_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get detailed analytics data for dashboard
        PRD Section 7 - Success Metrics
        """
        return await LazarusRepository.get_analytics_data(db, user_id, days)

    @staticmethod
    async def upgrade_to_pro(
        db: AsyncIOMotorDatabase, user_id: str
    ) -> Dict[str, Any]:
        """Upgrade user from BASIC (50 slots) to PRO (500 slots)"""
        slots = await LazarusRepository.upgrade_plan(
            db, user_id, LazarusPlanTypeEnum.PRO
        )

        if not slots:
            return {"success": False, "message": "Failed to upgrade plan"}

        return {
            "success": True,
            "message": "Successfully upgraded to PRO plan",
            "max_slots": slots.max_slots,
            "plan_type": slots.plan_type,
        }

    # ============ LEAD INTEGRATION ============
    @staticmethod
    async def mark_lead_as_dead(
        db: AsyncIOMotorDatabase,
        user_id: str,
        lead_id: str,
        reason: str,
        auto_monitor: bool = False,
    ) -> Dict[str, Any]:
        """
        Mark a lead as DEAD
        Optionally auto-add to Lazarus monitoring
        """
        # Update lead status to DEAD
        updated_lead = await LeadRepository.update_lead(
            db,
            lead_id,
            user_id,
            {
                "status": LeadStatusEnum.DEAD,
                "marked_dead_date": datetime.utcnow(),
                "marked_dead_reason": reason,
            },
        )

        if not updated_lead:
            return {"success": False, "message": "Lead not found"}

        # If auto_monitor is enabled, add to Lazarus
        if auto_monitor:
            # Determine type based on lead data
            if updated_lead.social_handle or updated_lead.username:
                # Add as focus contact
                contact_create = FocusContactCreate(
                    name=updated_lead.name or updated_lead.username or "Unknown",
                    social_handle=updated_lead.social_handle or updated_lead.username,
                    last_bio_text=updated_lead.bio,
                    industry_keywords=[],
                )
                monitor_result = await LazarusService.add_focus_contact(
                    db, user_id, contact_create, source_lead_id=lead_id
                )
            elif updated_lead.company_name and updated_lead.company_url:
                # Add as company monitor
                monitor_create = CompanyMonitorCreate(
                    company_name=updated_lead.company_name,
                    website_url=updated_lead.company_url,
                    last_homepage_content=None,
                    last_job_count=0,
                )
                monitor_result = await LazarusService.add_company_monitor(
                    db, user_id, monitor_create, source_lead_id=lead_id
                )
            else:
                monitor_result = {
                    "success": False,
                    "message": "Lead does not have required data for monitoring",
                }

            return {
                "success": True,
                "message": "Lead marked as DEAD and added to monitoring",
                "monitoring_added": monitor_result["success"],
                "monitoring_message": monitor_result.get("message"),
            }

        return {"success": True, "message": "Lead marked as DEAD"}

    @staticmethod
    async def resurrect_lead(
        db: AsyncIOMotorDatabase,
        user_id: str,
        lead_id: str,
        alert_type: str,
    ) -> Dict[str, Any]:
        """
        Resurrect a DEAD lead (change status to RESURRECTED)
        PRD Section 5.2: Resurrection
        """
        lead = await LeadRepository.get_lead(db, lead_id, user_id)
        if not lead:
            return {"success": False, "message": "Lead not found"}

        # Update lead to RESURRECTED
        updated_lead = await LeadRepository.update_lead(
            db,
            lead_id,
            user_id,
            {
                "status": LeadStatusEnum.RESURRECTED,
                "resurrection_count": (lead.resurrection_count or 0) + 1,
                "last_resurrection_date": datetime.utcnow(),
                "last_resurrection_type": alert_type,
                "source": LeadSourceEnum.LAZARUS,
            },
        )

        if not updated_lead:
            return {"success": False, "message": "Failed to resurrect lead"}

        return {
            "success": True,
            "message": "Lead resurrected successfully",
            "resurrection_count": updated_lead.resurrection_count,
        }
