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
from app.domain.schemas.lead_schema import LeadUpdate


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

        # If this contact is being created from an individual lead, fetch the lead to copy already-revealed email/phone
        lead_email = None
        lead_phone = None
        if source_lead_id:
            print(f"[LAZARUS] 📋 Fetching lead data from source_lead_id: {source_lead_id}")
            lead_response = await LeadRepository.get_lead_by_id(db, source_lead_id)
            lead_data = lead_response.get("lead") if lead_response else None
            if lead_data:
                # Copy already-revealed email and phone from lead (they already paid for these)
                lead_email_value = lead_data.get("lead_email") or lead_data.get("email")
                if lead_email_value and lead_email_value not in ["PROCESSING", "UNAVAILABLE", ""]:
                    lead_email = lead_email_value
                    print(f"[LAZARUS] 📧 Copying email from lead: {lead_email}")
                if lead_data.get("phone") and lead_data.get("phone") not in ["PROCESSING", "UNAVAILABLE", ""]:
                    lead_phone = lead_data.get("phone")
                    print(f"[LAZARUS] 📱 Copying phone from lead: {lead_phone}")

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

        # Clean LinkedIn URL to remove tracking parameters
        if linkedin_url:
            linkedin_url = SocialURLHelper.clean_linkedin_url(linkedin_url)
            print(f"[LAZARUS] Cleaned LinkedIn URL: {linkedin_url}")

        # Check for duplicates - prevent adding the same contact twice
        if linkedin_url or twitter_url:
            existing_contact = await LazarusRepository.find_duplicate_focus_contact(
                db, user_id, linkedin_url, twitter_url
            )
            if existing_contact:
                platform = "LinkedIn" if linkedin_url else "Twitter"
                return {
                    "success": False,
                    "message": f"This contact is already being monitored. Duplicate {platform} profile detected.",
                    "duplicate_focus_id": existing_contact.focus_id,
                    "duplicate_name": existing_contact.name,
                }

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

        # Add already-revealed email/phone from lead if available (they already paid for this)
        if lead_email:
            contact_data["email"] = lead_email
        if lead_phone:
            contact_data["phone"] = lead_phone

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
            update_data = LeadUpdate(
                is_lazarus_monitored=True,
                lazarus_focus_id=contact_data["focus_id"],
                lead_status=LeadStatusEnum.MONITORING,
            )
            await LeadRepository.update_lead(
                db,
                source_lead_id,
                update_data,
            )

        # Auto-trigger enrichment if LinkedIn URL is provided
        # This ensures profile photo, email, and other data are immediately available
        print(f"[LAZARUS] 🔍 Checking if enrichment needed...")
        print(f"[LAZARUS] 🔍 LinkedIn URL exists: {bool(linkedin_url)}")
        print(f"[LAZARUS] 🔍 LinkedIn URL value: {linkedin_url}")

        if linkedin_url:
            from app.services.LinkedInProfileScraperService import LinkedInProfileScraperService

            print(f"[LAZARUS] 🚀 AUTO-ENRICHMENT STARTING...")
            print(f"[LAZARUS] 👤 Contact: {contact_create.name}")
            print(f"[LAZARUS] 🔗 LinkedIn URL: {linkedin_url}")

            try:
                # Update status to pending
                await LazarusRepository.update_focus_contact(
                    db, contact_data["focus_id"], user_id, {"enrichment_status": "pending"}
                )

                # Call Bright Data LinkedIn Profile Enrichment Service (FREE - no credits)
                from app.services.BrightDataProfileEnrichmentService import BrightDataProfileEnrichmentService
                enrichment_service = BrightDataProfileEnrichmentService()
                enrichment_result = await enrichment_service.enrich_profile(
                    linkedin_url=linkedin_url,
                    timeout_seconds=90
                )

                if enrichment_result.get("success"):
                    profile_data = enrichment_result.get("profile", {})

                    # Log what Bright Data returned
                    print(f"[LAZARUS] ✅ Enrichment successful!")
                    print(f"[LAZARUS] 📧 Email: {profile_data.get('email') or 'Not found'}")
                    print(f"[LAZARUS] 📱 Phone: {profile_data.get('phone') or 'Not found'}")
                    print(f"[LAZARUS] 📸 Profile Photo: {'✅ Found' if profile_data.get('profile_photo') else '❌ Not found'}")
                    print(f"[LAZARUS] 💼 Headline: {profile_data.get('headline')[:50] if profile_data.get('headline') else 'Not found'}...")
                    print(f"[LAZARUS] 🏢 Current Company: {profile_data.get('current_company') or 'Not found'}")
                    print(f"[LAZARUS] 📍 Location: {profile_data.get('location') or 'Not found'}")
                    print(f"[LAZARUS] 🔗 Connections: {profile_data.get('connections_count') or 'Not found'}")
                    print(f"[LAZARUS] 📋 About: {'✅ Found' if profile_data.get('about') else '❌ Not found'}")
                    print(f"[LAZARUS] 💪 Skills: {len(profile_data.get('skills', [])) if profile_data.get('skills') else 0} skills")
                    print(f"[LAZARUS] 🎓 Education: {len(profile_data.get('education', [])) if profile_data.get('education') else 0} entries")
                    print(f"[LAZARUS] 💼 Work Experience: {len(profile_data.get('work_experience', [])) if profile_data.get('work_experience') else 0} entries")

                    # Check if any actual profile data was retrieved
                    has_profile_data = any([
                        profile_data.get("profile_photo"),
                        profile_data.get("email"),
                        profile_data.get("phone"),
                        profile_data.get("current_company"),
                        profile_data.get("headline"),
                        profile_data.get("about")
                    ])

                    if has_profile_data:
                        # Update contact with enriched data from Bright Data
                        # IMPORTANT: Don't overwrite email/phone if they were copied from lead (user already paid)
                        update_data = {
                            "profile_photo": profile_data.get("profile_photo"),
                            "headline": profile_data.get("headline"),
                            "location": profile_data.get("location"),
                            "connections_count": profile_data.get("connections_count"),
                            "about": profile_data.get("about"),
                            "current_company": profile_data.get("current_company") or contact_data.get("current_company"),
                            "current_position": profile_data.get("current_position"),
                            "work_experience": profile_data.get("work_experience"),
                            "education": profile_data.get("education"),
                            "skills": profile_data.get("skills"),
                            "languages": profile_data.get("languages"),
                            "certifications": profile_data.get("certifications"),
                            "enrichment_status": "completed",
                            "enriched_at": datetime.utcnow()
                        }

                        # Only add email/phone from Bright Data if NOT already copied from lead
                        if not lead_email:
                            update_data["email"] = profile_data.get("email")
                        if not lead_phone:
                            update_data["phone"] = profile_data.get("phone")

                        # Remove None values
                        update_data = {k: v for k, v in update_data.items() if v is not None}

                        # Debug: Log what we're about to save
                        print(f"[LAZARUS] 📝 Saving enriched data to DB:")
                        for key, value in update_data.items():
                            if key == 'about':
                                print(f"   {key}: {str(value)[:100]}...")
                            elif isinstance(value, (list, dict)):
                                print(f"   {key}: {type(value)} with {len(value)} items")
                            else:
                                print(f"   {key}: {value}")

                        await LazarusRepository.update_focus_contact(
                            db, contact_data["focus_id"], user_id, update_data
                        )

                        print(f"[LAZARUS] ✅ Auto-enrichment successful for {contact_create.name}")
                    else:
                        # API returned success but no profile data (profile inaccessible/private)
                        await LazarusRepository.update_focus_contact(
                            db, contact_data["focus_id"], user_id, {
                                "enrichment_status": "failed",
                                "enriched_at": datetime.utcnow()
                            }
                        )
                        print(f"[LAZARUS] ⚠️  Profile inaccessible or private - no data retrieved")
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

        # Auto-trigger enrichment if Twitter URL is provided
        if twitter_url:
            from app.services.TwitterEnrichmentService import TwitterEnrichmentService

            print(f"[LAZARUS] 🐦 AUTO-ENRICHMENT STARTING (Twitter)...")
            print(f"[LAZARUS] 👤 Contact: {contact_create.name}")
            print(f"[LAZARUS] 🔗 Twitter URL: {twitter_url}")

            try:
                # Update status to pending
                await LazarusRepository.update_focus_contact(
                    db, contact_data["focus_id"], user_id, {"enrichment_status": "pending"}
                )

                # Call Twitter enrichment service (Bright Data)
                twitter_service = TwitterEnrichmentService()
                profile_data = await twitter_service.enrich_profile(
                    twitter_url_or_handle=twitter_url,
                    max_posts=5  # Get 5 posts for enrichment snapshot
                )

                if profile_data:
                    print(f"[LAZARUS] ✅ Twitter enrichment successful!")
                    print(f"[LAZARUS] 📸 Profile: {profile_data.get('profile_name')}")
                    print(f"[LAZARUS] 👥 Followers: {profile_data.get('followers', 0):,}")
                    print(f"[LAZARUS] ✓ Verified: {profile_data.get('is_verified')}")

                    try:
                        # Transform to FocusContact format
                        enrichment_data = twitter_service.transform_to_focus_contact_data(profile_data)
                        print(f"[LAZARUS] 🔧 Transform completed, type: {type(enrichment_data)}")

                        # Remove None values - but keep nested dicts like twitter_data
                        enrichment_data = {
                            k: v for k, v in enrichment_data.items()
                            if v is not None and v != ""
                        }
                        print(f"[LAZARUS] 🔧 After filtering None values, keys: {list(enrichment_data.keys())}")

                        print(f"[LAZARUS] 📝 Saving Twitter enriched data to DB:")
                        print(f"   Profile Photo: {'✅ Found' if enrichment_data.get('profile_photo') else '❌ Not found'}")
                        print(f"   Twitter Handle: @{enrichment_data.get('twitter_handle')}")
                        print(f"   Twitter ID: {enrichment_data.get('twitter_id')}")

                        # Safely access nested twitter_data
                        twitter_data = enrichment_data.get('twitter_data')
                        if twitter_data and isinstance(twitter_data, dict):
                            print(f"   Followers: {twitter_data.get('followers', 0):,}")
                        else:
                            print(f"   Followers: twitter_data not available")

                        # Save enriched data to database
                        await LazarusRepository.update_focus_contact(
                            db, contact_data["focus_id"], user_id, enrichment_data
                        )

                        print(f"[LAZARUS] ✅ Twitter auto-enrichment completed for: {contact_create.name}")

                    except Exception as transform_error:
                        print(f"[LAZARUS] ❌ Transform error: {str(transform_error)}")
                        import traceback
                        traceback.print_exc()
                        raise
                else:
                    print(f"[LAZARUS] ⚠️  Twitter enrichment failed - no profile data returned")
                    await LazarusRepository.update_focus_contact(
                        db, contact_data["focus_id"], user_id, {
                            "enrichment_status": "failed",
                            "enriched_at": datetime.utcnow()
                        }
                    )

            except Exception as e:
                print(f"[LAZARUS] ⚠️  Twitter auto-enrichment error: {str(e)}")
                # Don't fail the whole operation if enrichment fails
                import traceback
                traceback.print_exc()

        # Fetch the final enriched contact to return to frontend
        enriched_contact = await LazarusRepository.get_focus_contact_by_id(
            db, contact_data["focus_id"], user_id
        )

        return {
            "success": True,
            "message": "Focus contact added successfully" + (" and enrichment started" if (linkedin_url or twitter_url) else ""),
            "focus_id": contact_data["focus_id"],
            "slots_used": slots.used_slots + 1,
            "slots_available": slots.max_slots - (slots.used_slots + 1),
            "contact": enriched_contact,  # Return full enriched contact data
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
            update_data = LeadUpdate(
                is_lazarus_monitored=False,
                lazarus_focus_id=None,
            )
            await LeadRepository.update_lead(
                db,
                contact.source_lead_id,
                update_data,
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
            update_data = LeadUpdate(
                is_lazarus_monitored=True,
                lazarus_company_monitor_id=monitor_data["monitor_id"],
                lead_status=LeadStatusEnum.MONITORING,
            )
            await LeadRepository.update_lead(
                db,
                source_lead_id,
                update_data,
            )

        # Auto-trigger enrichment if LinkedIn URL is provided
        linkedin_url = monitor_create.linkedin_url
        if linkedin_url:
            from app.services.BrightDataCompanyEnrichmentService import BrightDataCompanyEnrichmentService

            print(f"[LAZARUS] Auto-enriching company: {monitor_create.company_name}")
            print(f"[LAZARUS] LinkedIn URL: {linkedin_url}")

            try:
                # Update status to pending
                await LazarusRepository.update_company_monitor(
                    db, monitor_data["monitor_id"], user_id, {"enrichment_status": "pending"}
                )

                # Call company enrichment service
                company_service = BrightDataCompanyEnrichmentService()
                enrichment_result = await company_service.enrich_company(
                    linkedin_url=linkedin_url,
                    timeout_seconds=60
                )

                print(f"[LAZARUS] Company enrichment result success: {enrichment_result.get('success')}")

                if enrichment_result.get("success"):
                    # Map company data to CompanyMonitor fields
                    update_data = {
                        "logo": enrichment_result.get("logo"),
                        "company_image": enrichment_result.get("company_image"),
                        "about": enrichment_result.get("about"),
                        "slogan": enrichment_result.get("slogan"),
                        "description": enrichment_result.get("description"),
                        "specialties": enrichment_result.get("specialties"),
                        "organization_type": enrichment_result.get("organization_type"),
                        "company_size": enrichment_result.get("company_size"),
                        "industries": enrichment_result.get("industries"),
                        "founded": enrichment_result.get("founded"),
                        "headquarters": enrichment_result.get("headquarters"),
                        "followers": enrichment_result.get("followers"),
                        "employees": enrichment_result.get("employees"),
                        "enriched_at": datetime.utcnow(),
                        "enrichment_status": "completed"
                    }

                    # Remove None values
                    update_data = {k: v for k, v in update_data.items() if v is not None}

                    print(f"[LAZARUS] Updating company with enriched data: {list(update_data.keys())}")

                    # Save enriched data to database
                    await LazarusRepository.update_company_monitor(
                        db, monitor_data["monitor_id"], user_id, update_data
                    )

                    print(f"[LAZARUS] ✅ Company auto-enrichment completed for: {monitor_create.company_name}")
                else:
                    error_msg = enrichment_result.get("error_message", "Unknown error")
                    print(f"[LAZARUS] ⚠️  Company enrichment failed: {error_msg}")
                    await LazarusRepository.update_company_monitor(
                        db, monitor_data["monitor_id"], user_id, {"enrichment_status": "failed"}
                    )

            except Exception as e:
                print(f"[LAZARUS] ⚠️  Company auto-enrichment error: {str(e)}")
                import traceback
                traceback.print_exc()

        return {
            "success": True,
            "message": "Company monitor added successfully" + (" and enrichment started" if linkedin_url else ""),
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
            update_data = LeadUpdate(
                is_lazarus_monitored=False,
                lazarus_company_monitor_id=None,
            )
            await LeadRepository.update_lead(
                db,
                monitor.source_lead_id,
                update_data,
            )

        return {"success": True, "message": "Company monitor removed successfully"}

    # ============ BULK CSV UPLOAD ============
    @staticmethod
    async def bulk_upload_from_csv(
        db: AsyncIOMotorDatabase,
        user_id: str,
        csv_rows: List[CSVUploadRow],
        auto_enrich: bool = False
    ) -> Dict[str, Any]:
        """
        Bulk upload focus contacts/companies from CSV
        PRD Section 4.2: Bulk Upload via CSV

        Enhanced Features:
        - Accepts full URLs or handles (auto-parsed via SocialURLHelper)
        - Duplicate detection based on LinkedIn/Twitter URLs
        - Optional auto-enrichment for LinkedIn profiles
        - Detailed feedback on URL parsing and normalization

        Args:
            db: Database connection
            user_id: User ID
            csv_rows: List of CSV rows to upload
            auto_enrich: If True, auto-trigger LinkedIn enrichment for contacts with LinkedIn URLs

        Returns:
            Dictionary with upload results, errors, and detailed feedback
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
        duplicate_count = 0
        enrichment_queued_count = 0
        errors = []
        uploaded_contacts = []

        for row in csv_rows:
            try:
                if row.type == LazarusMonitorTypeEnum.FOCUS_CONTACT:
                    # Parse social_handle to extract platform URLs
                    parsed_urls = {}
                    detected_platform = "Unknown"
                    normalized_url = None

                    if row.social_handle:
                        parsed_urls = SocialURLHelper.parse_social_handle(row.social_handle)
                        detected_platform = (
                            "LinkedIn" if parsed_urls.get("linkedin_url") else
                            "Twitter" if parsed_urls.get("twitter_url") else
                            "Facebook" if parsed_urls.get("facebook_url") else
                            "Instagram" if parsed_urls.get("instagram_url") else
                            "Unknown"
                        )
                        normalized_url = (
                            parsed_urls.get("linkedin_url") or
                            parsed_urls.get("twitter_url") or
                            parsed_urls.get("facebook_url") or
                            parsed_urls.get("instagram_url")
                        )

                    # Check for duplicates based on LinkedIn or Twitter URL
                    is_duplicate = False
                    if parsed_urls.get("linkedin_url"):
                        # Clean LinkedIn URL for duplicate check
                        clean_linkedin_url = SocialURLHelper.clean_linkedin_url(parsed_urls["linkedin_url"])
                        existing = await db["focus_contacts"].find_one({
                            "user_id": user_id,
                            "linkedin_url": clean_linkedin_url
                        })
                        if existing:
                            is_duplicate = True
                            duplicate_count += 1
                            errors.append({
                                "name": row.name,
                                "error": f"Duplicate: Contact with LinkedIn URL '{clean_linkedin_url}' already exists",
                                "is_duplicate": True
                            })
                    elif parsed_urls.get("twitter_url"):
                        existing = await db["focus_contacts"].find_one({
                            "user_id": user_id,
                            "twitter_url": parsed_urls["twitter_url"]
                        })
                        if existing:
                            is_duplicate = True
                            duplicate_count += 1
                            errors.append({
                                "name": row.name,
                                "error": f"Duplicate: Contact with Twitter URL '{parsed_urls['twitter_url']}' already exists",
                                "is_duplicate": True
                            })

                    # Skip if duplicate
                    if is_duplicate:
                        continue

                    # Create contact
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

                    if result["success"]:
                        added_count += 1

                        # Track uploaded contact with URL parsing feedback
                        uploaded_contacts.append({
                            "name": row.name,
                            "focus_id": result.get("focus_id"),
                            "original_input": row.social_handle,
                            "detected_platform": detected_platform,
                            "normalized_url": normalized_url,
                            "enrichment_queued": False
                        })

                        # Auto-enrich if requested and LinkedIn URL exists
                        if auto_enrich and parsed_urls.get("linkedin_url"):
                            try:
                                await LazarusService._enrich_focus_contact_background(
                                    db,
                                    user_id,
                                    result["focus_id"],
                                    parsed_urls["linkedin_url"]
                                )
                                enrichment_queued_count += 1
                                uploaded_contacts[-1]["enrichment_queued"] = True
                                print(f"✅ Queued enrichment for {row.name} (LinkedIn: {parsed_urls['linkedin_url']})")
                            except Exception as enrich_error:
                                print(f"⚠️ Enrichment queue failed for {row.name}: {str(enrich_error)}")
                    else:
                        failed_count += 1
                        errors.append({"name": row.name, "error": result["message"]})

                else:  # COMPANY
                    # Check for duplicate company by website URL
                    is_duplicate = False
                    if row.website_url:
                        existing = await db["company_monitors"].find_one({
                            "user_id": user_id,
                            "website_url": row.website_url
                        })
                        if existing:
                            is_duplicate = True
                            duplicate_count += 1
                            errors.append({
                                "name": row.name,
                                "error": f"Duplicate: Company with website '{row.website_url}' already exists",
                                "is_duplicate": True
                            })

                    # Skip if duplicate
                    if is_duplicate:
                        continue

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
                        uploaded_contacts.append({
                            "name": row.name,
                            "monitor_id": result.get("monitor_id"),
                            "website_url": row.website_url,
                            "type": "COMPANY"
                        })
                    else:
                        failed_count += 1
                        errors.append({"name": row.name, "error": result["message"]})

            except Exception as e:
                failed_count += 1
                errors.append({"name": row.name, "error": str(e)})
                print(f"❌ Error uploading {row.name}: {str(e)}")
                import traceback
                traceback.print_exc()

        # Build summary message
        message_parts = [f"Uploaded {added_count} monitors"]
        if failed_count > 0:
            message_parts.append(f"{failed_count} failed")
        if duplicate_count > 0:
            message_parts.append(f"{duplicate_count} duplicates skipped")
        if enrichment_queued_count > 0:
            message_parts.append(f"{enrichment_queued_count} queued for enrichment")

        message = ". ".join(message_parts) + "."

        return {
            "success": True,
            "message": message,
            "added_count": added_count,
            "failed_count": failed_count,
            "duplicate_count": duplicate_count,
            "enrichment_queued_count": enrichment_queued_count,
            "errors": errors,
            "uploaded_contacts": uploaded_contacts,
        }

    @staticmethod
    async def _enrich_focus_contact_background(
        db: AsyncIOMotorDatabase,
        user_id: str,
        focus_id: str,
        linkedin_url: str
    ) -> None:
        """
        Background enrichment helper for CSV uploads
        Enriches LinkedIn profile and updates focus contact

        Args:
            db: Database connection
            user_id: User ID
            focus_id: Focus contact ID
            linkedin_url: LinkedIn URL to enrich
        """
        from app.services.BrightDataProfileEnrichmentService import BrightDataProfileEnrichmentService

        # Update status to pending
        await LazarusRepository.update_focus_contact(
            db, focus_id, user_id, {"enrichment_status": "pending"}
        )

        # Call Bright Data LinkedIn Profile Enrichment Service
        enrichment_service = BrightDataProfileEnrichmentService()
        enrichment_result = await enrichment_service.enrich_profile(
            linkedin_url=linkedin_url,
            timeout_seconds=90
        )

        if not enrichment_result.get("success"):
            # Mark as failed
            await LazarusRepository.update_focus_contact(
                db, focus_id, user_id, {
                    "enrichment_status": "failed",
                    "enriched_at": datetime.utcnow()
                }
            )
            print(f"⚠️ Enrichment failed for focus_id {focus_id}: {enrichment_result.get('error_message')}")
            return

        # Extract enriched data
        profile_data = enrichment_result.get("profile_data", {})

        # Update contact with enriched data
        enrichment_update = {
            "email": enrichment_result.get("email"),
            "phone": enrichment_result.get("phone"),
            "linkedin_url": linkedin_url,
            "profile_photo": profile_data.get("profile_photo"),
            "headline": profile_data.get("headline"),
            "location": profile_data.get("location"),
            "connections_count": profile_data.get("connections_count"),
            "about": profile_data.get("about"),
            "work_experience": profile_data.get("work_experience"),
            "education": profile_data.get("education"),
            "skills": profile_data.get("skills"),
            "languages": profile_data.get("languages"),
            "certifications": profile_data.get("certifications"),
            "enriched_at": datetime.utcnow(),
            "enrichment_status": "completed"
        }

        # Update current_company if available
        if profile_data.get("current_company"):
            enrichment_update["current_company"] = profile_data.get("current_company")

        await LazarusRepository.update_focus_contact(
            db, focus_id, user_id, enrichment_update
        )

        print(f"✅ Successfully enriched focus_id {focus_id}")
        if enrichment_result.get("email"):
            print(f"   📧 Email: {enrichment_result.get('email')}")
        if enrichment_result.get("phone"):
            print(f"   📱 Phone: {enrichment_result.get('phone')}")

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
            update_data = LeadUpdate(
                lead_status=LeadStatusEnum.CONTACTED,
            )
            await LeadRepository.update_lead(
                db,
                updated.resurrected_lead_id,
                update_data,
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
        update_data = LeadUpdate(
            lead_status=LeadStatusEnum.DEAD,
            marked_dead_date=datetime.utcnow(),
            marked_dead_reason=reason,
        )
        updated_lead_response = await LeadRepository.update_lead(
            db,
            lead_id,
            update_data,
        )

        updated_lead_data = updated_lead_response.get("lead") if updated_lead_response else None
        if not updated_lead_data:
            return {"success": False, "message": "Lead not found"}

        # If auto_monitor is enabled, add to Lazarus
        if auto_monitor:
            # Determine type based on lead data
            if updated_lead_data.get("social_handle") or updated_lead_data.get("username"):
                # Add as focus contact
                contact_create = FocusContactCreate(
                    name=updated_lead_data.get("first_name") or updated_lead_data.get("username") or "Unknown",
                    social_handle=updated_lead_data.get("social_handle") or updated_lead_data.get("username"),
                    last_bio_text=updated_lead_data.get("bio"),
                    industry_keywords=[],
                )
                monitor_result = await LazarusService.add_focus_contact(
                    db, user_id, contact_create, source_lead_id=lead_id
                )
            elif updated_lead_data.get("company_name") and updated_lead_data.get("company_url"):
                # Add as company monitor
                monitor_create = CompanyMonitorCreate(
                    company_name=updated_lead_data.get("company_name"),
                    website_url=updated_lead_data.get("company_url"),
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
        lead_response = await LeadRepository.get_lead_by_id(db, lead_id)
        lead_data = lead_response.get("lead") if lead_response else None
        if not lead_data:
            return {"success": False, "message": "Lead not found"}

        # Convert to Lead object for easier access
        from app.domain.schemas.lead_schema import Lead
        lead = Lead(**lead_data)

        # Update lead to RESURRECTED
        update_data = LeadUpdate(
            lead_status=LeadStatusEnum.RESURRECTED,
            resurrection_count=(lead.resurrection_count or 0) + 1,
            last_resurrection_date=datetime.utcnow(),
            last_resurrection_type=alert_type,
            lead_source=LeadSourceEnum.LAZARUS,
        )
        updated_lead = await LeadRepository.update_lead(
            db,
            lead_id,
            update_data,
        )

        if not updated_lead:
            return {"success": False, "message": "Failed to resurrect lead"}

        return {
            "success": True,
            "message": "Lead resurrected successfully",
            "resurrection_count": updated_lead.resurrection_count,
        }
