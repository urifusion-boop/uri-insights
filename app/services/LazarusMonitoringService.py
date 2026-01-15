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
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.LazarusRepository import LazarusRepository
from app.services.LazarusService import LazarusService
from app.services.AIService import AIService
from app.services.OpenAIApifyTwitterService import OpenAIApifyTwitterService
from app.services.ApifyGoogleSearchService import ApifyGoogleSearchService
from app.services.ApifyLinkedInJobsService import ApifyLinkedInJobsService
from app.services.XUsersLookupService import XUsersLookupService
from app.domain.requests.twitter_requests import CurrentUserLookupParams
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
import logging

logger = logging.getLogger(__name__)


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

                # Update scan metadata using custom scan frequency
                scan_frequency = contact.scan_frequency_days if hasattr(contact, 'scan_frequency_days') else 7
                await LazarusRepository.update_focus_contact(
                    db,
                    contact.focus_id,
                    contact.user_id,
                    {
                        "last_scan_date": datetime.utcnow(),
                        "next_scan_date": datetime.utcnow() + timedelta(days=scan_frequency),
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
        PRD Section 4.2: Origami Method - Batch processing to save costs
        """
        # Build Origami query
        handles_query = " OR ".join([f"from:{h}" for h in handles])
        keywords_query = " OR ".join([f'"{k}"' for k in keywords[:5]])  # Limit to 5 keywords

        query = f"({handles_query}) AND ({keywords_query})"

        logger.info(f"🔍 Lazarus Origami Query: {query}")

        try:
            # Use existing OpenAIApifyTwitterService to fetch tweets
            twitter_service = OpenAIApifyTwitterService()
            result = await twitter_service.fetch_tweets_with_analysis(
                keyword=query,
                max_tweets=100,
                analyze_sentiment=False  # We'll do our own analysis
            )

            if not result.get("success"):
                logger.warning(f"Twitter fetch failed: {result.get('error_message', 'Unknown error')}")
                return []

            tweets = result.get("tweets", [])
            logger.info(f"✅ Fetched {len(tweets)} tweets via Origami method")

            # Transform to our format and map to handles
            formatted_tweets = []
            for tweet in tweets:
                # Extract handle from author username
                author = tweet.get("author", {})
                handle = author.get("username") if isinstance(author, dict) else str(author)

                formatted_tweets.append({
                    "handle": handle,
                    "text": tweet.get("text", ""),
                    "url": tweet.get("url", ""),
                    "created_at": tweet.get("created_at", ""),
                    "author": author
                })

            return formatted_tweets

        except Exception as e:
            logger.error(f"Error in _fetch_batch_tweets: {str(e)}")
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

            # Detect cash injection (funding news)
            cash_alert = await LazarusMonitoringService._detect_cash_injection(
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
            for alert in [hiring_alert, cash_alert, pivot_alert, dead_alert]:
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

            # Update scan metadata using custom scan frequency
            scan_frequency = monitor.scan_frequency_days if hasattr(monitor, 'scan_frequency_days') else 7
            await LazarusRepository.update_company_monitor(
                db,
                monitor.monitor_id,
                monitor.user_id,
                {
                    "last_scan_date": datetime.utcnow(),
                    "next_scan_date": datetime.utcnow() + timedelta(days=scan_frequency),
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
        PRD Section 3 Track A: Hiring Spree
        Logic: Job_Count_Current > Job_Count_Prev + 2
        """
        try:
            # Use existing ApifyLinkedInJobsService to fetch current job count
            linkedin_service = ApifyLinkedInJobsService()

            # Use monitor's location if specified, otherwise omit (no location filter)
            location = monitor.location if hasattr(monitor, 'location') and monitor.location else None

            result = await linkedin_service.fetch_job_postings(
                search_query=f"company:{monitor.company_name}",
                max_jobs=100,  # Just to count, we don't need details
                location=location  # None = no location filter
            )

            if not result.get("success"):
                logger.warning(f"Failed to fetch jobs for {monitor.company_name}: {result.get('error_message')}")
                return None

            current_job_count = result.get("total_jobs", 0)
            previous_job_count = monitor.last_job_count or 0

            logger.info(f"📊 {monitor.company_name}: Previous jobs: {previous_job_count}, Current jobs: {current_job_count}")

            # PRD Logic: Trigger if increased by 3+
            if current_job_count >= previous_job_count + 3:
                # Update job count in monitor
                await LazarusRepository.update_company_monitor(
                    db,
                    monitor.monitor_id,
                    monitor.user_id,
                    {"last_job_count": current_job_count},
                )

                job_increase = current_job_count - previous_job_count

                logger.info(f"🔥 HIRING SPREE DETECTED: {monitor.company_name} added {job_increase} new jobs!")

                # Create HIRING_SPREE alert
                return {
                    "alert_id": str(uuid.uuid4()),
                    "user_id": monitor.user_id,
                    "source_type": LazarusMonitorTypeEnum.COMPANY,
                    "source_id": monitor.monitor_id,
                    "alert_type": LazarusAlertTypeEnum.HIRING_SPREE,
                    "alert_message": f"Expansion Detected: {monitor.company_name} added {job_increase} new roles",
                    "evidence": {
                        "detected_date": datetime.utcnow().isoformat(),
                        "signal_source": "LinkedIn Jobs",
                        "old_value": str(previous_job_count),
                        "new_value": str(current_job_count),
                        "tweets": None,
                    },
                    "suggested_pitch": f"I noticed {monitor.company_name} is expanding rapidly with {job_increase} new roles. This seems like a great time to discuss how we can support your growth.",
                    "status": LazarusAlertStatusEnum.NEW,
                    "resurrected_lead_id": monitor.source_lead_id,
                    "created_date": datetime.utcnow(),
                    "last_updated": datetime.utcnow(),
                }

            return None

        except Exception as e:
            logger.error(f"Error detecting hiring spree for {monitor.company_name}: {str(e)}")
            return None

    @staticmethod
    async def _detect_cash_injection(
        db: AsyncIOMotorDatabase, monitor: CompanyMonitor
    ) -> Optional[Dict[str, Any]]:
        """
        Detect cash injection via Google News
        PRD Section 3 Track A: Cash Injection
        Logic: Google News result for "{Company}" + "Raised" exists
        """
        try:
            # Use existing ApifyGoogleSearchService for news detection
            google_service = ApifyGoogleSearchService()

            # Build dork query for funding news
            dork_query = f'"{monitor.company_name}" ("raised" OR "funding" OR "investment" OR "Series A" OR "Series B" OR "grant")'

            logger.info(f"🔍 Searching for cash injection: {dork_query}")

            # Use monitor's country_code if specified, otherwise use "us" for global results
            country_code = monitor.country_code if hasattr(monitor, 'country_code') and monitor.country_code else "us"

            results = await google_service.search(
                dork_query=dork_query,
                max_results=10,
                country_code=country_code
            )

            # If we found recent funding news
            if results and len(results) > 0:
                # Check if news is recent (within last 30 days)
                recent_news = [r for r in results if r.source_date and
                               (datetime.utcnow() - r.source_date.replace(tzinfo=None)).days <= 30]

                if recent_news:
                    news_item = recent_news[0]

                    logger.info(f"💰 CASH INJECTION DETECTED: {monitor.company_name} - {news_item.title}")

                    return {
                        "alert_id": str(uuid.uuid4()),
                        "user_id": monitor.user_id,
                        "source_type": LazarusMonitorTypeEnum.COMPANY,
                        "source_id": monitor.monitor_id,
                        "alert_type": LazarusAlertTypeEnum.CASH_INJECTION,
                        "alert_message": f"New Budget Detected: {monitor.company_name} raised fresh funding",
                        "evidence": {
                            "detected_date": datetime.utcnow().isoformat(),
                            "signal_source": f"Google News - {news_item.url}",
                            "old_value": None,
                            "new_value": news_item.title,
                            "tweets": [news_item.snippet],
                        },
                        "suggested_pitch": f"Congratulations on the recent funding! This seems like a perfect time to discuss how we can help {monitor.company_name} scale.",
                        "status": LazarusAlertStatusEnum.NEW,
                        "resurrected_lead_id": monitor.source_lead_id,
                        "created_date": datetime.utcnow(),
                        "last_updated": datetime.utcnow(),
                    }

            return None

        except Exception as e:
            logger.error(f"Error detecting cash injection for {monitor.company_name}: {str(e)}")
            return None

    @staticmethod
    async def _detect_strategic_pivot(
        db: AsyncIOMotorDatabase, monitor: CompanyMonitor
    ) -> Optional[Dict[str, Any]]:
        """
        Detect strategic pivot via Google News
        PRD Section 3 Track A: The Pivot
        Logic: News about "New", "Launch", "Now serving", "Expansion"
        """
        try:
            # Use Google search to detect pivot announcements
            google_service = ApifyGoogleSearchService()

            # Build dork query for pivot signals
            dork_query = f'"{monitor.company_name}" ("new launch" OR "now serving" OR "expansion" OR "new product" OR "rebranding")'

            logger.info(f"🔍 Searching for strategic pivot: {dork_query}")

            # Use monitor's country_code if specified, otherwise use "us" for global results
            country_code = monitor.country_code if hasattr(monitor, 'country_code') and monitor.country_code else "us"

            results = await google_service.search(
                dork_query=dork_query,
                max_results=10,
                country_code=country_code
            )

            # If we found recent pivot news
            if results and len(results) > 0:
                recent_news = [r for r in results if r.source_date and
                               (datetime.utcnow() - r.source_date.replace(tzinfo=None)).days <= 60]

                if recent_news:
                    news_item = recent_news[0]

                    logger.info(f"🔄 STRATEGIC PIVOT DETECTED: {monitor.company_name} - {news_item.title}")

                    return {
                        "alert_id": str(uuid.uuid4()),
                        "user_id": monitor.user_id,
                        "source_type": LazarusMonitorTypeEnum.COMPANY,
                        "source_id": monitor.monitor_id,
                        "alert_type": LazarusAlertTypeEnum.STRATEGIC_PIVOT,
                        "alert_message": f"Strategic Pivot Detected: {monitor.company_name} is offering new services",
                        "evidence": {
                            "detected_date": datetime.utcnow().isoformat(),
                            "signal_source": f"Google News - {news_item.url}",
                            "old_value": None,
                            "new_value": news_item.title,
                            "tweets": [news_item.snippet],
                        },
                        "suggested_pitch": f"I saw the news about {monitor.company_name}'s new direction. Would love to discuss how we can support this pivot.",
                        "status": LazarusAlertStatusEnum.NEW,
                        "resurrected_lead_id": monitor.source_lead_id,
                        "created_date": datetime.utcnow(),
                        "last_updated": datetime.utcnow(),
                    }

            return None

        except Exception as e:
            logger.error(f"Error detecting pivot for {monitor.company_name}: {str(e)}")
            return None

    @staticmethod
    async def _detect_company_dead(
        db: AsyncIOMotorDatabase, monitor: CompanyMonitor
    ) -> Optional[Dict[str, Any]]:
        """
        Detect company dead (website returns 404 for 4 weeks)
        PRD Section 3 Track A: The Obituary
        Logic: Website returns 404 Error (Offline) for 4 weeks in a row
        """
        try:
            # Check website status
            logger.info(f"🔍 Checking website status for {monitor.company_name}: {monitor.website_url}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(monitor.website_url, follow_redirects=True)
                    status_code = response.status_code
                except Exception as e:
                    logger.warning(f"Website check failed for {monitor.website_url}: {str(e)}")
                    status_code = 404  # Assume dead if any error

            logger.info(f"📊 {monitor.company_name} website status: {status_code}")

            # Track consecutive 404 counts
            consecutive_404s = monitor.consecutive_404_count if hasattr(monitor, 'consecutive_404_count') else 0

            if status_code == 404 or status_code >= 500:
                consecutive_404s += 1

                # Update monitor with new 404 count
                await LazarusRepository.update_company_monitor(
                    db,
                    monitor.monitor_id,
                    monitor.user_id,
                    {"consecutive_404_count": consecutive_404s},
                )

                # PRD Logic: 4 weeks in a row = 4 scans (weekly scans)
                if consecutive_404s >= 4:
                    logger.warning(f"☠️ COMPANY DEAD: {monitor.company_name} - 404 for {consecutive_404s} weeks")

                    return {
                        "alert_id": str(uuid.uuid4()),
                        "user_id": monitor.user_id,
                        "source_type": LazarusMonitorTypeEnum.COMPANY,
                        "source_id": monitor.monitor_id,
                        "alert_type": LazarusAlertTypeEnum.COMPANY_DEAD,
                        "alert_message": f"Company appears extinct: {monitor.company_name} website offline for 4 weeks. Delete to clean list.",
                        "evidence": {
                            "detected_date": datetime.utcnow().isoformat(),
                            "signal_source": f"Website Check - {monitor.website_url}",
                            "old_value": "Online",
                            "new_value": f"404 Error ({consecutive_404s} weeks)",
                            "tweets": None,
                        },
                        "suggested_pitch": None,  # No pitch needed for dead companies
                        "status": LazarusAlertStatusEnum.NEW,
                        "resurrected_lead_id": monitor.source_lead_id,
                        "created_date": datetime.utcnow(),
                        "last_updated": datetime.utcnow(),
                    }
            else:
                # Website is alive, reset consecutive 404 count
                if consecutive_404s > 0:
                    await LazarusRepository.update_company_monitor(
                        db,
                        monitor.monitor_id,
                        monitor.user_id,
                        {"consecutive_404_count": 0},
                    )

            return None

        except Exception as e:
            logger.error(f"Error checking if company dead for {monitor.company_name}: {str(e)}")
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
