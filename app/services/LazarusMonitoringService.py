"""
Lazarus Monitoring Service - Background scanning using Origami Method
PRD Section 6: Origami Method (Batch Processing)

This service runs weekly background scans to detect:
- Job changes (Focus Contacts)
- Company hiring sprees (Company Monitors)
- Business pivots and cash injections
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.LazarusRepository import LazarusRepository
from app.services.LazarusService import LazarusService
from app.services.AIService import AIService
from app.domain.schemas.lazarus_schema import (
    FocusContact,
    CompanyMonitor,
    LazarusAlert,
    LazarusAlertTypeEnum,
    LazarusAlertStatusEnum,
    LazarusMonitorTypeEnum,
    LazarusMonitoringStatusEnum,
    LazarusAlertEvidence,
)


class LazarusMonitoringService:
    """Background service for weekly Lazarus scans using Origami Method"""

    # ============ FOCUS CONTACT SCANNING ============
    @staticmethod
    async def scan_focus_contacts(db: AsyncIOMotorDatabase, batch_size: int = 100):
        """
        Scan focus contacts for job changes and buying signals
        PRD Section 6.1: Origami Query Construction
        """
        print("🔍 Starting Focus Contact scan...")

        # Get contacts due for scanning
        contacts = await LazarusRepository.get_contacts_for_scan(db, batch_size)

        if not contacts:
            print("✅ No focus contacts due for scanning")
            return {"scanned": 0, "alerts_created": 0}

        # Group contacts by user for batch processing (Origami Method)
        user_batches: Dict[str, List[FocusContact]] = {}
        for contact in contacts:
            if contact.user_id not in user_batches:
                user_batches[contact.user_id] = []
            user_batches[contact.user_id].append(contact)

        total_scanned = 0
        total_alerts = 0

        # Process each user's batch
        for user_id, user_contacts in user_batches.items():
            print(f"📦 Processing batch for user {user_id}: {len(user_contacts)} contacts")

            # Build Origami query: (from:Handle1 OR from:Handle2) AND ("keywords")
            handles = [
                c.social_handle for c in user_contacts if c.social_handle
            ]

            if not handles:
                continue

            # Collect all industry keywords from all contacts
            all_keywords = []
            for contact in user_contacts:
                all_keywords.extend(contact.industry_keywords)

            # Batch process using Twitter/X API (or Apify)
            results = await LazarusMonitoringService._fetch_batch_tweets(
                db, handles, all_keywords
            )

            # Analyze each contact's results
            for contact in user_contacts:
                contact_results = [
                    r for r in results if r.get("handle") == contact.social_handle
                ]

                # Detect job changes and buying signals
                alert = await LazarusMonitoringService._analyze_focus_contact(
                    db, contact, contact_results
                )

                if alert:
                    # Create alert
                    await LazarusRepository.create_alert(db, alert)
                    total_alerts += 1

                    # Increment alert count on contact
                    await LazarusRepository.update_focus_contact(
                        db,
                        contact.focus_id,
                        contact.user_id,
                        {"alert_count": contact.alert_count + 1},
                    )

                # Update scan metadata
                await LazarusRepository.update_focus_contact(
                    db,
                    contact.focus_id,
                    contact.user_id,
                    {
                        "last_scan_date": datetime.utcnow(),
                        "next_scan_date": datetime.utcnow() + timedelta(days=7),
                        "scan_count": contact.scan_count + 1,
                    },
                )

                total_scanned += 1

        print(f"✅ Focus Contact scan complete: {total_scanned} scanned, {total_alerts} alerts")
        return {"scanned": total_scanned, "alerts_created": total_alerts}

    @staticmethod
    async def _fetch_batch_tweets(
        db: AsyncIOMotorDatabase, handles: List[str], keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Fetch tweets using Origami batch query
        Query format: (from:Handle1 OR from:Handle2) AND ("keyword1" OR "keyword2")
        """
        # Build Origami query
        handles_query = " OR ".join([f"from:{h}" for h in handles])
        keywords_query = " OR ".join([f'"{k}"' for k in keywords[:5]])  # Limit to 5 keywords

        query = f"({handles_query}) AND ({keywords_query})"

        # TODO: Integrate with existing TwitterService or ApifyTwitterService
        # For now, return mock data structure
        print(f"🔍 Origami Query: {query}")

        # In production, this would call:
        # results = await TwitterService.search_tweets(db, query, max_results=100)

        # Return mock structure for now
        return []

    @staticmethod
    async def _analyze_focus_contact(
        db: AsyncIOMotorDatabase, contact: FocusContact, tweets: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze focus contact for signals
        PRD Section 5.1: Detection Logic
        """
        # Check for bio changes (job exit detection)
        bio_changed = False
        new_bio_text = None

        # In production, fetch current bio from Twitter API
        # current_bio = await TwitterService.get_user_bio(contact.social_handle)

        # For now, simulate bio check
        current_bio_hash = contact.last_bio_hash

        # Example: If bio hash changed, it's a potential job change
        # if current_bio_hash != contact.last_bio_hash:
        #     bio_changed = True
        #     new_bio_text = current_bio

        # Analyze tweets for buying signals using AI
        if tweets:
            buying_intent_detected = await LazarusMonitoringService._detect_buying_intent(
                db, tweets, contact.industry_keywords
            )

            if buying_intent_detected:
                # Create BUYING_INTENT alert
                return {
                    "alert_id": str(uuid.uuid4()),
                    "user_id": contact.user_id,
                    "source_type": LazarusMonitorTypeEnum.FOCUS_CONTACT,
                    "source_id": contact.focus_id,
                    "alert_type": LazarusAlertTypeEnum.BUYING_INTENT,
                    "alert_message": f"{contact.name} is showing buying intent signals",
                    "evidence": {
                        "detected_date": datetime.utcnow().isoformat(),
                        "signal_source": "Twitter/X",
                        "tweets": [t.get("text", "") for t in tweets[:3]],
                        "old_value": None,
                        "new_value": None,
                    },
                    "suggested_pitch": None,  # TODO: Generate AI pitch
                    "status": LazarusAlertStatusEnum.NEW,
                    "resurrected_lead_id": contact.source_lead_id,
                    "created_date": datetime.utcnow(),
                    "last_updated": datetime.utcnow(),
                }

        return None

    @staticmethod
    async def _detect_buying_intent(
        db: AsyncIOMotorDatabase, tweets: List[Dict[str, Any]], keywords: List[str]
    ) -> bool:
        """Use AI to detect buying intent in tweets"""
        # TODO: Integrate with existing IntentAnalysisService
        # For now, simple keyword matching
        for tweet in tweets:
            text = tweet.get("text", "").lower()
            for keyword in keywords:
                if keyword.lower() in text:
                    # Check for buying signals: "looking for", "need", "recommend", etc.
                    buying_signals = ["looking for", "need", "recommend", "anyone know", "suggestions"]
                    if any(signal in text for signal in buying_signals):
                        return True
        return False

    # ============ COMPANY MONITOR SCANNING ============
    @staticmethod
    async def scan_company_monitors(db: AsyncIOMotorDatabase, batch_size: int = 100):
        """
        Scan companies for hiring sprees, funding, pivots
        PRD Section 3 Track A: Company Monitoring
        """
        print("🔍 Starting Company Monitor scan...")

        # Get monitors due for scanning
        monitors = await LazarusRepository.get_monitors_for_scan(db, batch_size)

        if not monitors:
            print("✅ No company monitors due for scanning")
            return {"scanned": 0, "alerts_created": 0}

        total_scanned = 0
        total_alerts = 0

        for monitor in monitors:
            # Detect hiring spree (job count increase)
            hiring_alert = await LazarusMonitoringService._detect_hiring_spree(
                db, monitor
            )

            # Detect homepage changes (pivot detection)
            pivot_alert = await LazarusMonitoringService._detect_strategic_pivot(
                db, monitor
            )

            # Detect 404s (company dead)
            dead_alert = await LazarusMonitoringService._detect_company_dead(
                db, monitor
            )

            # Create alerts if detected
            for alert in [hiring_alert, pivot_alert, dead_alert]:
                if alert:
                    await LazarusRepository.create_alert(db, alert)
                    total_alerts += 1

                    # Increment alert count
                    await LazarusRepository.update_company_monitor(
                        db,
                        monitor.monitor_id,
                        monitor.user_id,
                        {"alert_count": monitor.alert_count + 1},
                    )

            # Update scan metadata
            await LazarusRepository.update_company_monitor(
                db,
                monitor.monitor_id,
                monitor.user_id,
                {
                    "last_scan_date": datetime.utcnow(),
                    "next_scan_date": datetime.utcnow() + timedelta(days=7),
                    "scan_count": monitor.scan_count + 1,
                },
            )

            total_scanned += 1

        print(f"✅ Company Monitor scan complete: {total_scanned} scanned, {total_alerts} alerts")
        return {"scanned": total_scanned, "alerts_created": total_alerts}

    @staticmethod
    async def _detect_hiring_spree(
        db: AsyncIOMotorDatabase, monitor: CompanyMonitor
    ) -> Optional[Dict[str, Any]]:
        """
        Detect hiring spree (job count increased by 3+ in a week)
        PRD Section 5.1.1: Hiring Spree
        """
        # TODO: Integrate with ApifyLinkedInJobsService or ApifyJobbermanService
        # Fetch current job count for company

        # Mock: Simulate job count fetch
        # current_job_count = await ApifyLinkedInJobsService.get_company_job_count(monitor.company_name)
        current_job_count = monitor.last_job_count  # Placeholder

        # Check if increased by 3+
        if current_job_count >= monitor.last_job_count + 3:
            # Update job count
            await LazarusRepository.update_company_monitor(
                db,
                monitor.monitor_id,
                monitor.user_id,
                {"last_job_count": current_job_count},
            )

            # Create HIRING_SPREE alert
            return {
                "alert_id": str(uuid.uuid4()),
                "user_id": monitor.user_id,
                "source_type": LazarusMonitorTypeEnum.COMPANY,
                "source_id": monitor.monitor_id,
                "alert_type": LazarusAlertTypeEnum.HIRING_SPREE,
                "alert_message": f"{monitor.company_name} is on a hiring spree! ({current_job_count - monitor.last_job_count} new jobs)",
                "evidence": {
                    "detected_date": datetime.utcnow().isoformat(),
                    "signal_source": "Job Boards",
                    "old_value": str(monitor.last_job_count),
                    "new_value": str(current_job_count),
                    "tweets": None,
                },
                "suggested_pitch": None,
                "status": LazarusAlertStatusEnum.NEW,
                "resurrected_lead_id": monitor.source_lead_id,
                "created_date": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
            }

        return None

    @staticmethod
    async def _detect_strategic_pivot(
        db: AsyncIOMotorDatabase, monitor: CompanyMonitor
    ) -> Optional[Dict[str, Any]]:
        """
        Detect strategic pivot (homepage content changed significantly)
        PRD Section 5.1.2: Strategic Pivot
        """
        # TODO: Integrate with FirecrawlService to scrape homepage
        # current_homepage = await FirecrawlService.scrape_url(monitor.website_url)

        # For now, return None (no pivot detected)
        return None

    @staticmethod
    async def _detect_company_dead(
        db: AsyncIOMotorDatabase, monitor: CompanyMonitor
    ) -> Optional[Dict[str, Any]]:
        """
        Detect company dead (3 consecutive 404s)
        PRD Section 5.1.3: Company Dead
        """
        # TODO: Check if website returns 404
        # status_code = await FirecrawlService.check_url_status(monitor.website_url)

        # For now, return None (company not dead)
        return None

    # ============ AI-POWERED PITCH GENERATION ============
    @staticmethod
    async def generate_suggested_pitch(
        db: AsyncIOMotorDatabase, alert: LazarusAlert
    ) -> Optional[str]:
        """
        Generate AI-powered pitch for resurrection
        PRD Section 5.2: Auto-generated pitch suggestion
        """
        # Build context from alert evidence
        context = f"""
        Alert Type: {alert.alert_type}
        Alert Message: {alert.alert_message}
        Evidence: {alert.evidence.model_dump_json()}
        """

        # TODO: Integrate with AIService to generate pitch
        # prompt = f"Generate a short, personalized pitch based on this resurrection signal:\n{context}"
        # pitch = await AIService.generate_text(db, prompt)

        # For now, return template
        return f"Hi! I noticed {alert.alert_message}. Would love to reconnect and see how we can help."

    # ============ SCHEDULER INTEGRATION ============
    @staticmethod
    async def run_weekly_scan(db: AsyncIOMotorDatabase):
        """
        Main entry point for weekly background scan
        Call this from APScheduler cron job
        """
        print("🚀 Starting Lazarus Protocol weekly scan...")

        # Scan focus contacts
        focus_results = await LazarusMonitoringService.scan_focus_contacts(db)

        # Scan company monitors
        company_results = await LazarusMonitoringService.scan_company_monitors(db)

        total_scanned = focus_results["scanned"] + company_results["scanned"]
        total_alerts = focus_results["alerts_created"] + company_results["alerts_created"]

        print(f"✅ Weekly scan complete: {total_scanned} monitors scanned, {total_alerts} alerts created")

        return {
            "success": True,
            "total_scanned": total_scanned,
            "total_alerts": total_alerts,
            "focus_contacts": focus_results,
            "company_monitors": company_results,
        }
