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
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.repository.LazarusRepository import LazarusRepository
from app.services.LazarusService import LazarusService
from app.services.AIService import AIService
from app.services.OpenAIApifyTwitterService import OpenAIApifyTwitterService
from app.services.ApifyGoogleSearchService import ApifyGoogleSearchService
from app.services.ApifyLinkedInJobsService import ApifyLinkedInJobsService
from app.services.ApifyLinkedInPostScraperService import ApifyLinkedInPostScraperService
from app.services.XUsersLookupService import XUsersLookupService
# Note: BrightDataLinkedInPostsService is kept for profile/company enrichment only
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

    # ============ URL NORMALIZATION ============
    @staticmethod
    def _normalize_post_url(url: str) -> str:
        """
        Normalize post URL by removing tracking parameters that change between requests.

        LinkedIn tracking parameters to remove:
        - utm_source, utm_medium, utm_campaign (Google Analytics)
        - rcm (LinkedIn tracking parameter - changes per request)
        - trk (LinkedIn tracking)

        This ensures the same post is recognized even if fetched multiple times.
        """
        if not url:
            return url

        try:
            parsed = urlparse(url)

            # Get query parameters
            query_params = parse_qs(parsed.query)

            # Remove tracking parameters
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
                             'rcm', 'trk', 'trackingId', 'refId', 'ref']
            for param in tracking_params:
                query_params.pop(param, None)

            # Rebuild query string
            new_query = urlencode(query_params, doseq=True)

            # Rebuild URL
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))

            return normalized

        except Exception:
            # If normalization fails, return original URL
            return url

    # ============ AI PRIORITY SCORING ============
    @staticmethod
    def calculate_priority_score(alert: Dict[str, Any]) -> tuple[int, str]:
        """
        Calculate AI priority score for an alert (0-100)

        Factors:
        - Signal confidence (0-40 points)
        - Recency (0-30 points) - how recent the signal was detected
        - Signal type priority (0-30 points)

        Returns:
            Tuple of (score, level) where level is "HOT", "WARM", or "COLD"
        """
        score = 0

        # Factor 1: Signal confidence (0-40 points)
        confidence = alert.get("evidence", {}).get("confidence", 0.5)
        score += int(confidence * 40)

        # Factor 2: Recency (0-30 points)
        created_at = alert.get("created_at", datetime.utcnow())
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        hours_since_detection = (datetime.utcnow() - created_at).total_seconds() / 3600
        if hours_since_detection < 4:
            score += 30  # Very fresh - contact NOW
        elif hours_since_detection < 24:
            score += 20  # Within 24 hours
        elif hours_since_detection < 72:
            score += 10  # Within 3 days
        # else: 0 points (older than 3 days)

        # Factor 3: Signal type priority (0-30 points) - Enhanced for 11 signals
        signal_type = alert.get("evidence", {}).get("signal_type", "").lower()
        alert_type = alert.get("alert_type", "")

        # Career Change Signals = HIGHEST priority (30 points)
        if signal_type in ["promoted", "changed_jobs", "new_decision_maker"] or "PROMOTED" in str(alert_type) or "CHANGED_JOBS" in str(alert_type):
            score += 30  # Fresh start, new budget, looking for tools
        # Pain + Switch Signals = HIGH priority (25-28 points)
        elif signal_type == "competitor_complaint":
            score += 28  # Complaining about competitor = ready to switch NOW
        elif signal_type in ["pain", "switch"] or "SWITCH" in str(alert_type):
            score += 25  # Has problem or actively looking
        # Business Growth Signals = MEDIUM-HIGH priority (20-22 points)
        elif signal_type == "expansion" or "EXPANSION" in str(alert_type):
            score += 22  # Scaling, has budget
        elif signal_type in ["raised_funds", "funding"] or "CASH_INJECTION" in str(alert_type):
            score += 20  # Has fresh capital
        elif signal_type == "hiring" or "HIRING_SPREE" in str(alert_type):
            score += 18  # Growing team
        # Engagement Signals = WARM priority (15 points)
        elif signal_type in ["interacts_with_content", "likes_competitor"]:
            score += 15  # Warm lead, knows about you
        else:
            score += 10  # Other signals

        # Determine level
        if score >= 80:
            level = "HOT"
        elif score >= 50:
            level = "WARM"
        else:
            level = "COLD"

        return (score, level)

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
        all_fetched_posts = []  # Store sample posts to return to frontend

        # Process each user's batch
        for user_id, user_contacts in user_batches.items():
            print(f"📦 Processing batch for user {user_id}: {len(user_contacts)} contacts")

            # Separate contacts by monitoring source intelligently
            from app.core.helpers.social_url_helper import SocialURLHelper

            contacts_with_linkedin = []
            contacts_with_twitter = []
            contacts_with_tiktok = []
            contacts_with_facebook = []

            for contact in user_contacts:
                # Priority 1: Explicit URL fields
                if contact.linkedin_url:
                    contacts_with_linkedin.append(contact)
                elif contact.twitter_url:
                    contacts_with_twitter.append(contact)
                # Priority 2: Detect from social_handle
                elif contact.social_handle:
                    url_type = SocialURLHelper.detect_url_type(contact.social_handle)
                    if url_type == "linkedin":
                        contacts_with_linkedin.append(contact)
                    elif url_type == "twitter":
                        contacts_with_twitter.append(contact)
                    elif url_type == "facebook":
                        contacts_with_facebook.append(contact)
                    elif url_type == "instagram":
                        contacts_with_tiktok.append(contact)  # TikTok for now, will add Instagram later

            # Log routing decision
            print(f"🔀 Contact Routing:")
            print(f"   LinkedIn: {len(contacts_with_linkedin)}, Twitter: {len(contacts_with_twitter)}, TikTok: {len(contacts_with_tiktok)}, Facebook: {len(contacts_with_facebook)}")
            if contacts_with_linkedin:
                for c in contacts_with_linkedin:
                    print(f"   ✅ {c.name} → LinkedIn Scraper")
            if contacts_with_twitter:
                for c in contacts_with_twitter:
                    print(f"   ✅ {c.name} → Twitter Scraper")
            if contacts_with_tiktok:
                for c in contacts_with_tiktok:
                    print(f"   ✅ {c.name} → TikTok Scraper")
            if contacts_with_facebook:
                for c in contacts_with_facebook:
                    print(f"   ✅ {c.name} → Facebook Scraper")

            # Fetch Twitter posts (existing Origami method)
            twitter_results = []
            if contacts_with_twitter:
                # Build Origami query: (from:Handle1 OR from:Handle2) AND ("keywords")
                handles = [c.social_handle for c in contacts_with_twitter if c.social_handle]

                if handles:
                    # Collect all industry keywords from all contacts
                    all_keywords = []
                    for contact in contacts_with_twitter:
                        all_keywords.extend(contact.industry_keywords)

                    # Batch process using Twitter/X API (or Apify)
                    twitter_results = await LazarusMonitoringService._fetch_batch_tweets(
                        db, handles, all_keywords
                    )

            # Fetch LinkedIn posts
            linkedin_posts_by_focus_id = {}
            if contacts_with_linkedin:
                linkedin_posts_by_focus_id = await LazarusMonitoringService._fetch_linkedin_posts(
                    db, contacts_with_linkedin
                )
                # Add sample posts to response
                for posts in linkedin_posts_by_focus_id.values():
                    all_fetched_posts.extend(posts[:3])  # First 3 posts from each contact

            # Fetch TikTok posts
            tiktok_posts_by_focus_id = {}
            if contacts_with_tiktok:
                tiktok_posts_by_focus_id = await LazarusMonitoringService._fetch_tiktok_posts(
                    db, contacts_with_tiktok
                )

            # Fetch Facebook posts
            facebook_posts_by_focus_id = {}
            if contacts_with_facebook:
                facebook_posts_by_focus_id = await LazarusMonitoringService._fetch_facebook_posts(
                    db, contacts_with_facebook
                )

            # Analyze each contact's results from ALL platforms
            for contact in user_contacts:
                # Get posts from each platform
                contact_tweets = [r for r in twitter_results if r.get("handle") == contact.social_handle]
                contact_linkedin_posts = linkedin_posts_by_focus_id.get(contact.focus_id, [])
                contact_tiktok_posts = tiktok_posts_by_focus_id.get(contact.focus_id, [])
                contact_facebook_posts = facebook_posts_by_focus_id.get(contact.focus_id, [])

                # Combine all posts for analysis
                all_posts = contact_linkedin_posts + contact_tiktok_posts + contact_facebook_posts

                # Detect job changes and buying signals from ALL sources
                alert = await LazarusMonitoringService._analyze_focus_contact(
                    db, contact, contact_tweets, all_posts
                )

                if alert:
                    # Calculate priority score
                    alert_dict = alert.dict() if hasattr(alert, 'dict') else alert
                    priority_score, priority_level = LazarusMonitoringService.calculate_priority_score(alert_dict)
                    alert_dict["priority_score"] = priority_score
                    alert_dict["priority_level"] = priority_level

                    # Create alert
                    await LazarusRepository.create_alert(db, alert_dict)
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
        return {
            "scanned": total_scanned,
            "alerts_created": total_alerts,
            "sample_posts": all_fetched_posts[:10]  # Return max 10 sample posts
        }

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
    async def _fetch_linkedin_posts(
        db: AsyncIOMotorDatabase, contacts_with_linkedin: List[FocusContact]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch LinkedIn posts for contacts with LinkedIn URLs
        Returns posts grouped by contact's focus_id for easy mapping
        """
        if not contacts_with_linkedin:
            return {}

        try:
            # Extract LinkedIn URLs from contacts
            linkedin_urls = []
            url_to_focus_id = {}  # Map URL back to contact

            for contact in contacts_with_linkedin:
                if contact.linkedin_url:
                    linkedin_urls.append(contact.linkedin_url)
                    url_to_focus_id[contact.linkedin_url] = contact.focus_id

            if not linkedin_urls:
                logger.warning("No valid LinkedIn URLs found in contacts")
                return {}

            logger.info(f"🔍 Fetching LinkedIn posts for {len(linkedin_urls)} contacts")
            print(f"🔍 LinkedIn URLs to fetch: {linkedin_urls}")

            # Use Apify LinkedIn Posts Service to fetch posts (more accurate than Bright Data)
            # Bright Data is reserved for profile/company enrichment only
            linkedin_service = ApifyLinkedInPostScraperService()
            print(f"🔧 Calling Apify to fetch LinkedIn posts...")
            result = await linkedin_service.fetch_linkedin_posts(
                linkedin_urls=linkedin_urls,
                limit_per_source=10,  # 10 posts per contact (2-4 weeks of activity)
                deep_scrape=True  # Enable detailed scraping
            )
            print(f"🔧 Apify fetch returned: success={result.get('success')}, total_posts={result.get('total_posts', 0)}")

            if not result.get("success"):
                error_msg = result.get('error_message', 'Unknown error')
                logger.warning(f"LinkedIn post fetch failed: {error_msg}")
                print(f"❌ LinkedIn post fetch failed: {error_msg}")
                return {}

            posts_by_url = result.get("posts_by_url", {})

            # Convert from URL-based mapping to focus_id-based mapping
            posts_by_focus_id = {}
            for url, posts in posts_by_url.items():
                focus_id = url_to_focus_id.get(url)
                if focus_id:
                    posts_by_focus_id[focus_id] = posts

            total_posts = sum(len(posts) for posts in posts_by_focus_id.values())
            logger.info(f"✅ Fetched {total_posts} LinkedIn posts from {len(posts_by_focus_id)} contacts")

            # Log the actual posts for visibility
            for focus_id, posts in posts_by_focus_id.items():
                print(f"\n📝 LinkedIn Posts for contact {focus_id}:")
                for i, post in enumerate(posts[:3], 1):  # Show first 3 posts
                    print(f"   Post {i}: {post.get('text', 'No text')[:150]}...")
                    print(f"   Author: {post.get('author', 'Unknown')}")
                    print(f"   Date: {post.get('created_at', 'Unknown')}")
                    print(f"   Engagement: {post.get('likes', 0)} likes, {post.get('comments', 0)} comments")
                    print(f"   ---")

            return posts_by_focus_id

        except Exception as e:
            logger.error(f"Error in _fetch_linkedin_posts: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    @staticmethod
    async def _fetch_twitter_posts(
        db: AsyncIOMotorDatabase, contacts_with_twitter: List[FocusContact]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch Twitter/X posts for contacts with Twitter URLs
        Returns: {focus_id: [posts]}
        """
        if not contacts_with_twitter:
            return {}

        try:
            print(f"🐦 Fetching Twitter posts for {len(contacts_with_twitter)} contact(s)...")

            # For single contact scan, fetch ALL recent posts without keyword filtering
            posts_by_focus_id = {}

            for contact in contacts_with_twitter:
                # Extract handle from URL or social_handle
                handle = None
                if contact.twitter_url:
                    handle = contact.twitter_url.rstrip('/').split('/')[-1]
                elif contact.social_handle:
                    handle = contact.social_handle.rstrip('/').split('/')[-1]

                if not handle:
                    print(f"❌ No Twitter handle found for {contact.name}")
                    continue

                # Remove @ if present
                handle = handle.lstrip('@')

                # Build query to get ALL recent posts from this user
                query = f"from:{handle}"
                print(f"   Fetching tweets with query: {query}")

                try:
                    twitter_service = OpenAIApifyTwitterService()
                    result = await twitter_service.fetch_tweets_with_analysis(
                        keyword=query,
                        max_tweets=50,  # Get last 50 tweets
                        analyze_sentiment=False
                    )

                    if result.get("success"):
                        tweets = result.get("tweets", [])
                        if tweets:
                            # Format tweets
                            formatted_tweets = []
                            for tweet in tweets:
                                author = tweet.get("author", {})
                                formatted_tweets.append({
                                    "handle": handle,
                                    "text": tweet.get("text", ""),
                                    "url": tweet.get("url", ""),
                                    "created_at": tweet.get("created_at", ""),
                                    "author": author,
                                    "likes": tweet.get("likes", 0),
                                    "retweets": tweet.get("retweets", 0),
                                    "replies": tweet.get("replies", 0)
                                })

                            posts_by_focus_id[contact.focus_id] = formatted_tweets
                            print(f"✅ Found {len(formatted_tweets)} tweets for {contact.name}")
                        else:
                            print(f"ℹ️  No tweets found for {contact.name}")
                    else:
                        print(f"❌ Twitter fetch failed for {contact.name}: {result.get('error_message')}")

                except Exception as e:
                    logger.error(f"Error fetching tweets for {contact.name}: {str(e)}")
                    continue

            return posts_by_focus_id

        except Exception as e:
            logger.error(f"Error in _fetch_twitter_posts: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    @staticmethod
    async def _fetch_tiktok_posts(
        db: AsyncIOMotorDatabase, contacts_with_tiktok: List[FocusContact]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch TikTok posts for contacts"""
        if not contacts_with_tiktok:
            return {}

        try:
            from app.services.OpenAIApifyTiktokService import OpenAIApifyTiktokService
            tiktok_service = OpenAIApifyTiktokService()
            posts_by_focus_id = {}

            logger.info(f"🔍 Fetching TikTok posts for {len(contacts_with_tiktok)} contacts")

            for contact in contacts_with_tiktok:
                # Use keywords as hashtags for TikTok search
                if contact.industry_keywords:
                    keyword = contact.industry_keywords[0]  # Use first keyword
                    result = await tiktok_service.fetch_posts_with_analysis(keyword, max_posts=10)
                    if result.get("success"):
                        posts_by_focus_id[contact.focus_id] = result.get("posts", [])

            total_posts = sum(len(posts) for posts in posts_by_focus_id.values())
            logger.info(f"✅ Fetched {total_posts} TikTok posts from {len(posts_by_focus_id)} contacts")
            return posts_by_focus_id

        except Exception as e:
            logger.error(f"Error in _fetch_tiktok_posts: {str(e)}")
            return {}

    @staticmethod
    async def _fetch_facebook_posts(
        db: AsyncIOMotorDatabase, contacts_with_facebook: List[FocusContact]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch Facebook posts for contacts"""
        if not contacts_with_facebook:
            return {}

        try:
            from app.services.OpenAIApifyFacebookService import OpenAIApifyFacebookService
            facebook_service = OpenAIApifyFacebookService()
            posts_by_focus_id = {}

            logger.info(f"🔍 Fetching Facebook posts for {len(contacts_with_facebook)} contacts")

            for contact in contacts_with_facebook:
                # Use keywords for Facebook search
                if contact.industry_keywords:
                    keyword = " ".join(contact.industry_keywords[:2])  # Use first 2 keywords
                    result = await facebook_service.fetch_posts_with_analysis(keyword, max_posts=10)
                    if result.get("success"):
                        posts_by_focus_id[contact.focus_id] = result.get("posts", [])

            total_posts = sum(len(posts) for posts in posts_by_focus_id.values())
            logger.info(f"✅ Fetched {total_posts} Facebook posts from {len(posts_by_focus_id)} contacts")
            return posts_by_focus_id

        except Exception as e:
            logger.error(f"Error in _fetch_facebook_posts: {str(e)}")
            return {}

    @staticmethod
    async def _auto_enrich_contact(
        db: AsyncIOMotorDatabase,
        contact: FocusContact
    ):
        """
        Auto-enrich contact with LinkedIn Profile Scraper after alert creation
        Phase 1: Contact Enrichment
        """
        try:
            from app.services.LinkedInProfileScraperService import LinkedInProfileScraperService

            logger.info(f"🔍 Auto-enriching contact: {contact.name}")

            # Mark as pending
            await LazarusRepository.update_focus_contact(
                db, contact.focus_id, contact.user_id, {"enrichment_status": "pending"}
            )

            # Call enrichment service
            scraper_service = LinkedInProfileScraperService()
            enrichment_result = await scraper_service.enrich_profile(
                linkedin_url=contact.linkedin_url,
                timeout_seconds=90
            )

            if not enrichment_result.get("success"):
                logger.warning(f"Enrichment failed for {contact.name}: {enrichment_result.get('error_message')}")
                await LazarusRepository.update_focus_contact(
                    db, contact.focus_id, contact.user_id, {
                        "enrichment_status": "failed",
                        "enriched_at": datetime.utcnow()
                    }
                )
                return

            # Extract enriched data
            profile_data = enrichment_result.get("profile_data", {})

            # Update contact with enriched data
            # Extract skill titles from objects if needed
            skills_data = profile_data.get("skills")
            if skills_data and isinstance(skills_data, list):
                # Convert {'title': 'Skill Name'} to just 'Skill Name'
                skills_list = []
                for skill in skills_data:
                    if isinstance(skill, dict) and 'title' in skill:
                        skills_list.append(skill['title'])
                    elif isinstance(skill, str):
                        skills_list.append(skill)
            else:
                skills_list = None

            enrichment_update = {
                "email": enrichment_result.get("email"),
                "phone": enrichment_result.get("phone"),
                "profile_photo": profile_data.get("profile_photo"),
                "headline": profile_data.get("headline"),
                "location": profile_data.get("location"),
                "connections_count": profile_data.get("connections_count"),
                "about": profile_data.get("about"),
                "work_experience": profile_data.get("work_experience"),
                "education": profile_data.get("education"),
                "skills": skills_list,
                "languages": profile_data.get("languages"),
                "certifications": profile_data.get("certifications"),
                "enriched_at": datetime.utcnow(),
                "enrichment_status": "completed"
            }

            # Update current_company if available
            if profile_data.get("current_company"):
                enrichment_update["current_company"] = profile_data.get("current_company")

            await LazarusRepository.update_focus_contact(
                db, contact.focus_id, contact.user_id, enrichment_update
            )

            logger.info(f"✅ Successfully auto-enriched contact: {contact.name}")
            if enrichment_result.get("email"):
                logger.info(f"   📧 Email: {enrichment_result.get('email')}")
            if enrichment_result.get("phone"):
                logger.info(f"   📱 Phone: {enrichment_result.get('phone')}")

        except Exception as e:
            logger.error(f"Error in auto-enrichment: {str(e)}")
            try:
                await LazarusRepository.update_focus_contact(
                    db, contact.focus_id, contact.user_id, {
                        "enrichment_status": "failed",
                        "enriched_at": datetime.utcnow()
                    }
                )
            except:
                pass

    @staticmethod
    async def _analyze_focus_contact(
        db: AsyncIOMotorDatabase,
        contact: FocusContact,
        tweets: List[Dict[str, Any]],
        linkedin_posts: List[Dict[str, Any]] = []
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze focus contact for signals from both Twitter and LinkedIn
        PRD Section 5.1: Detection Logic
        """
        # Fetch user's signal preferences from their settings
        # Default to all 9 content-based signal types (excluding metadata-based signals)
        user_signal_preferences = [
            # Career Change
            "promoted", "changed_jobs", "new_decision_maker",
            # Business Growth
            "raised_funds", "hiring", "expansion",
            # Pain/Interest
            "pain", "competitor_complaint", "switch"
        ]

        try:
            # Try to get user's AutoDetectionSettings
            settings = await db["auto_detection_settings"].find_one({"user_id": contact.user_id})
            if settings and settings.get("detection_rules", {}).get("signal_types"):
                user_signal_preferences = settings["detection_rules"]["signal_types"]
        except Exception as e:
            logger.warning(f"Could not fetch user signal preferences, using defaults: {e}")

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

        # Analyze tweets and LinkedIn posts for buying signals using AI
        if tweets or linkedin_posts:
            print(f"\n🤖 Analyzing content for {contact.name}:")
            print(f"   Tweets: {len(tweets)}")
            print(f"   LinkedIn/Social posts: {len(linkedin_posts)}")

            signal_analysis = await LazarusMonitoringService._detect_buying_intent(
                db, contact, tweets, linkedin_posts, user_signal_preferences
            )

            if signal_analysis and signal_analysis.get('signal_detected'):
                print(f"🎯 SIGNAL DETECTED!")
                print(f"   Type: {signal_analysis.get('signal_type')}")
                print(f"   Confidence: {signal_analysis.get('confidence')}")
                print(f"   Evidence: {signal_analysis.get('evidence', '')[:200]}...")
                # Map signal_type to alert_type (Enhanced with 11 signals)
                signal_type_map = {
                    # Career Change Signals
                    "promoted": LazarusAlertTypeEnum.PROMOTED,
                    "changed_jobs": LazarusAlertTypeEnum.CHANGED_JOBS,
                    "new_decision_maker": LazarusAlertTypeEnum.NEW_DECISION_MAKER,

                    # Business Growth Signals
                    "raised_funds": LazarusAlertTypeEnum.CASH_INJECTION,
                    "funding": LazarusAlertTypeEnum.CASH_INJECTION,  # alias
                    "hiring": LazarusAlertTypeEnum.HIRING_SPREE,
                    "expansion": LazarusAlertTypeEnum.EXPANSION,

                    # Pain Signals
                    "pain": LazarusAlertTypeEnum.PAIN_SIGNAL,
                    "competitor_complaint": LazarusAlertTypeEnum.COMPETITOR_COMPLAINT,

                    # Engagement Signals
                    "switch": LazarusAlertTypeEnum.SWITCH_SIGNAL,
                    "likes_competitor": LazarusAlertTypeEnum.LIKES_COMPETITOR,
                    "interacts_with_content": LazarusAlertTypeEnum.INTERACTS_WITH_CONTENT,
                }

                alert_type = signal_type_map.get(
                    signal_analysis.get("signal_type", "pain"),
                    LazarusAlertTypeEnum.BUYING_INTENT  # fallback
                )

                # Generate AI-powered pitch
                suggested_pitch = await LazarusMonitoringService._generate_ai_pitch(
                    db, contact, signal_analysis, tweets, linkedin_posts
                )

                # Determine signal source and platform
                sources = []
                primary_platform = None
                if linkedin_posts:
                    sources.append("LinkedIn")
                    primary_platform = "LinkedIn"
                if tweets:
                    sources.append("Twitter/X")
                    if not primary_platform:
                        primary_platform = "Twitter"

                signal_source = " + ".join(sources) + " (AI Analysis)" if sources else "Unknown"

                # Combine content for evidence
                all_content = []
                all_content.extend([p.get("text", "") for p in linkedin_posts[:3]])
                all_content.extend([t.get("text", "") for t in tweets[:3]])

                # Get the exact post that triggered the signal using AI-provided index
                primary_post = None
                post_url = None
                post_text = None
                post_author = None
                post_created_at = None
                post_likes = None
                post_comments = None

                # AI returns the index of the triggering post
                triggering_index = signal_analysis.get("triggering_post_index")

                # Combine all posts in order: tweets first, then LinkedIn posts (matching AI prompt order)
                all_posts_ordered = []
                all_posts_ordered.extend(tweets[:5])  # Up to 5 tweets
                all_posts_ordered.extend(linkedin_posts[:5])  # Up to 5 LinkedIn posts

                logger.info(f"🔍 POST INDEX DEBUG:")
                logger.info(f"   AI returned index: {triggering_index}")
                logger.info(f"   Total posts available: {len(all_posts_ordered)}")
                logger.info(f"   Tweets count: {len(tweets[:5])}, LinkedIn count: {len(linkedin_posts[:5])}")
                logger.info(f"   Primary platform: {primary_platform}")

                # Get the specific post by index
                if triggering_index is not None and 0 <= triggering_index < len(all_posts_ordered):
                    primary_post = all_posts_ordered[triggering_index]
                    # Log which post was selected
                    post_preview = (primary_post.get("text") or primary_post.get("content") or "")[:80]
                    logger.info(f"✅ Found triggering post at index {triggering_index}: {post_preview}...")
                else:
                    # Fallback: use the first post from primary platform
                    logger.warning(f"⚠️ AI did not return valid post index (got {triggering_index}), falling back to first post from {primary_platform}")
                    if primary_platform == "LinkedIn" and linkedin_posts:
                        primary_post = linkedin_posts[0]
                    elif primary_platform == "Twitter" and tweets:
                        primary_post = tweets[0]

                # Extract post data based on which platform it's from
                if primary_post:
                    # Determine if this is a LinkedIn or Twitter post
                    is_linkedin = primary_post in linkedin_posts if linkedin_posts else False
                    is_twitter = primary_post in tweets if tweets else False

                    if is_linkedin:
                        post_url = primary_post.get("url") or primary_post.get("postUrl") or primary_post.get("link")
                        post_text = primary_post.get("text") or primary_post.get("content")
                        post_author = primary_post.get("author", {}).get("name") if isinstance(primary_post.get("author"), dict) else primary_post.get("author")
                        post_created_at = primary_post.get("created_at") or primary_post.get("postedAt")
                        post_likes = primary_post.get("likes") or primary_post.get("numLikes")
                        post_comments = primary_post.get("comments") or primary_post.get("numComments")
                    elif is_twitter:
                        post_url = primary_post.get("url") or primary_post.get("tweet_url")
                        post_text = primary_post.get("text") or primary_post.get("content")
                        post_author = primary_post.get("author", {}).get("username") if isinstance(primary_post.get("author"), dict) else primary_post.get("author")
                        post_created_at = primary_post.get("created_at") or primary_post.get("createdAt")
                        post_likes = primary_post.get("likes") or primary_post.get("likeCount")
                        post_comments = primary_post.get("replies") or primary_post.get("replyCount")

                # Build scanned_posts array with all posts that were analyzed
                from app.domain.schemas.lazarus_schema import ScannedPost
                scanned_posts = []

                # Add all tweets
                for i, tweet in enumerate(tweets[:5]):
                    tweet_url = tweet.get("url") or tweet.get("tweet_url")
                    tweet_text = tweet.get("text") or tweet.get("content")
                    if tweet_url and tweet_text:
                        scanned_posts.append({
                            "post_url": tweet_url,
                            "post_text": tweet_text,
                            "post_platform": "Twitter",
                            "post_author": tweet.get("author", {}).get("username") if isinstance(tweet.get("author"), dict) else tweet.get("author"),
                            "post_created_at": tweet.get("created_at") or tweet.get("createdAt"),
                            "post_likes": tweet.get("likes") or tweet.get("likeCount"),
                            "post_comments": tweet.get("replies") or tweet.get("replyCount"),
                            "post_index": i  # Index in all_posts_ordered
                        })

                # Add all LinkedIn posts
                for i, linkedin_post in enumerate(linkedin_posts[:5]):
                    linkedin_url = linkedin_post.get("url") or linkedin_post.get("postUrl") or linkedin_post.get("link")
                    linkedin_text = linkedin_post.get("text") or linkedin_post.get("content")
                    if linkedin_url and linkedin_text:
                        scanned_posts.append({
                            "post_url": linkedin_url,
                            "post_text": linkedin_text,
                            "post_platform": "LinkedIn",
                            "post_author": linkedin_post.get("author", {}).get("name") if isinstance(linkedin_post.get("author"), dict) else linkedin_post.get("author"),
                            "post_created_at": linkedin_post.get("created_at") or linkedin_post.get("postedAt"),
                            "post_likes": linkedin_post.get("likes") or linkedin_post.get("numLikes"),
                            "post_comments": linkedin_post.get("comments") or linkedin_post.get("numComments"),
                            "post_index": len(tweets[:5]) + i  # Offset by number of tweets
                        })

                logger.info(f"📋 Created scanned_posts array with {len(scanned_posts)} posts")

                # Create alert with AI analysis (platform-agnostic)
                return {
                    "alert_id": str(uuid.uuid4()),
                    "user_id": contact.user_id,
                    "source_type": LazarusMonitorTypeEnum.FOCUS_CONTACT,
                    "source_id": contact.focus_id,
                    "source_name": contact.name,  # Required field
                    "alert_type": alert_type,
                    "alert_message": signal_analysis.get("reason", f"{contact.name} is showing buying intent signals"),
                    "evidence": {
                        "signal_source": signal_source,
                        "signal_type": signal_analysis.get("signal_type"),
                        "confidence": signal_analysis.get("confidence"),
                        "evidence_text": signal_analysis.get("evidence"),
                        # Platform-agnostic fields - THE POST THAT TRIGGERED THE ALERT
                        "post_url": post_url,
                        "post_text": post_text,  # ACTUAL post content
                        "post_platform": primary_platform,
                        "post_author": post_author,
                        "post_created_at": post_created_at,
                        "post_likes": post_likes,
                        "post_comments": post_comments,
                        # All scanned posts and triggering index
                        "scanned_posts": scanned_posts,
                        "triggering_post_index": triggering_index,
                        # Legacy field for backward compatibility
                        "tweet_text": post_text,  # ACTUAL post content
                        "tweet_url": post_url if primary_platform == "Twitter" else None,
                    },
                    "suggested_pitch": suggested_pitch,
                    "status": LazarusAlertStatusEnum.NEW,
                    "source_lead_id": contact.source_lead_id,
                }
            elif signal_analysis and not signal_analysis.get('signal_detected'):
                # Signal was analyzed but didn't qualify - return rejection info
                print(f"❌ NO SIGNAL DETECTED")
                print(f"   Rejection Reason: {signal_analysis.get('rejection_reason', 'No reason provided')}")
                return {
                    "signal_detected": False,
                    "rejection_reason": signal_analysis.get('rejection_reason'),
                    "confidence": signal_analysis.get('confidence', 0.0)
                }

        return None

    @staticmethod
    async def _detect_buying_intent(
        db: AsyncIOMotorDatabase,
        contact: FocusContact,
        tweets: List[Dict[str, Any]],
        linkedin_posts: List[Dict[str, Any]],
        user_signal_preferences: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Use AI to detect buying intent in tweets and LinkedIn posts based on user's signal preferences"""
        if not tweets and not linkedin_posts:
            return None

        # Import here to avoid circular dependency
        from app.services.AIService import AIService
        from app.domain.enums.ai_prompt import LazarusPrompt
        from app.domain.schemas.lazarus_schema import BuyingSignalAnalysis

        # Format tweets for AI analysis
        content_pieces = []

        # Add tweets
        for i, tweet in enumerate(tweets[:5]):  # Up to 5 tweets
            content_pieces.append(f"Twitter Post {i+1}: {tweet.get('text', '')}")

        # Add LinkedIn posts
        for i, post in enumerate(linkedin_posts[:5]):  # Up to 5 LinkedIn posts
            content_pieces.append(f"LinkedIn Post {i+1}: {post.get('text', '')}")

        # Combine all content
        combined_content = "\n\n".join(content_pieces)

        # Build AI prompt with user's signal preferences
        # Handle industry_keywords safely (could be None or empty list)
        keywords_str = ", ".join(contact.industry_keywords) if contact.industry_keywords else "None specified"

        # Debug logging for keywords
        print(f"🔑 Industry Keywords for {contact.name}: {keywords_str}")
        if not contact.industry_keywords:
            print(f"⚠️  WARNING: No industry keywords set for {contact.name}. Keyword-based alerts will be limited!")

        prompt = LazarusPrompt.ANALYZE_BUYING_SIGNALS.value.format(
            contact_name=contact.name,
            current_company=contact.current_company or "Unknown",
            keywords=keywords_str,
            signal_types=", ".join(user_signal_preferences),
            tweets=combined_content  # Now includes both Twitter and LinkedIn
        )

        # Get AI analysis
        try:
            ai_model = AIService.build_ai_model([
                AIService.construct_user_prompt(prompt)
            ])

            ai_response = await AIService.structured_chat_completion(
                ai_model, BuyingSignalAnalysis
            )

            result = AIService.extract_ai_result(ai_response)

            # Return signal if detected with high confidence
            if result.signal_detected and result.confidence >= 0.7:
                return {
                    "signal_detected": True,
                    "signal_type": result.signal_type,
                    "confidence": result.confidence,
                    "evidence": result.evidence,
                    "reason": result.reason,
                    "triggering_post_index": result.triggering_post_index,
                    "rejection_reason": None
                }
            else:
                # Return rejection reason when signal not detected or confidence too low
                rejection_reason = result.rejection_reason
                if not rejection_reason and result.signal_detected and result.confidence < 0.7:
                    # Fallback if AI didn't provide rejection_reason for low confidence
                    rejection_reason = f"Confidence score {result.confidence:.2f} below threshold (0.70). Weak {result.signal_type or 'signal'} detected but not strong enough."
                elif not rejection_reason:
                    # Fallback if AI didn't provide rejection_reason at all
                    rejection_reason = "No buying signals detected in scanned posts."

                return {
                    "signal_detected": False,
                    "signal_type": None,
                    "confidence": result.confidence,
                    "evidence": None,
                    "reason": None,
                    "triggering_post_index": None,
                    "rejection_reason": rejection_reason
                }

        except Exception as e:
            logger.error(f"❌ AI buying intent detection failed for {contact.name}: {e}")
            logger.error(f"   Contact ID: {contact.focus_id}")
            logger.error(f"   Posts analyzed: {len(tweets)} tweets, {len(linkedin_posts)} LinkedIn posts")

            # Store failure for monitoring and retry
            try:
                await db["ai_detection_failures"].insert_one({
                    "contact_id": contact.focus_id,
                    "contact_name": contact.name,
                    "user_id": contact.user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "post_count": len(tweets) + len(linkedin_posts),
                    "timestamp": datetime.utcnow(),
                    "retry_count": 0,
                    "next_retry": datetime.utcnow() + timedelta(hours=2)
                })
                logger.info(f"   Logged failure for retry in 2 hours")
            except Exception as log_error:
                logger.error(f"   Failed to log AI failure: {log_error}")

            # Return None - better no alert than wrong alert
            # Contact will be retried on next scan
            return None

        return None

    @staticmethod
    async def _generate_ai_pitch(
        db: AsyncIOMotorDatabase,
        contact: FocusContact,
        signal_analysis: Dict[str, Any],
        tweets: List[Dict[str, Any]],
        linkedin_posts: List[Dict[str, Any]] = []
    ) -> Optional[str]:
        """Generate AI-powered personalized pitch based on signal analysis from Twitter and LinkedIn"""
        from app.services.AIService import AIService
        from app.domain.enums.ai_prompt import LazarusPrompt

        try:
            # Format tweets and LinkedIn posts for context
            content_texts = []

            # Add tweets
            for tweet in tweets[:3]:
                content_texts.append(f"- (Twitter) {tweet.get('text', '')}")

            # Add LinkedIn posts
            for post in linkedin_posts[:3]:
                content_texts.append(f"- (LinkedIn) {post.get('text', '')}")

            combined_texts = "\n".join(content_texts)

            # Build AI prompt for pitch generation
            signal_type = signal_analysis.get("signal_type", "unknown")
            signal_type_display = signal_type.replace("_", " ").title()

            prompt = LazarusPrompt.GENERATE_PITCH.value.format(
                contact_name=contact.name,
                current_company=contact.current_company or "their company",
                alert_type=signal_type_display,
                alert_message=signal_analysis.get("reason", f"Detected {signal_type_display} signal"),
                evidence=signal_analysis.get("evidence", ""),
                business_context="our solution helps businesses improve their processes",
                recent_tweets=combined_texts  # Now includes both Twitter and LinkedIn
            )

            # Get AI-generated pitch
            ai_model = AIService.build_ai_model([
                AIService.construct_user_prompt(prompt)
            ])

            ai_response = await AIService.chat_completion(ai_model)
            pitch = AIService.extract_ai_result(ai_response)

            return pitch if pitch else None

        except Exception as e:
            logger.error(f"AI pitch generation failed: {e}")
            # Fallback to template-based pitch
            signal_type = signal_analysis.get("signal_type", "switch")
            fallback_pitches = {
                "pain": f"Hi {contact.name}, I noticed you mentioned some challenges. Would love to discuss how we might help.",
                "switch": f"Hi {contact.name}, saw you're exploring alternatives. Happy to share how we've helped similar companies.",
                "hiring": f"Hi {contact.name}, congrats on the team expansion! Let's discuss how we can support your growth.",
                "funding": f"Hi {contact.name}, congratulations on the funding! Great time to discuss scaling together."
            }
            return fallback_pitches.get(signal_type, f"Hi {contact.name}, let's reconnect!")

    # ============ SINGLE CONTACT SCANNING ============
    @staticmethod
    async def scan_single_focus_contact(db: AsyncIOMotorDatabase, user_id: str, focus_id: str):
        """
        Scan a single specific focus contact immediately
        Used when user clicks "Scan Now" on a specific contact
        """
        from datetime import timedelta
        print(f"🔍 Starting single contact scan for {focus_id}...")

        # Get the specific contact
        from app.repository.LazarusRepository import LazarusRepository
        contact = await LazarusRepository.get_focus_contact_by_id(db, focus_id, user_id)

        if not contact:
            return {
                "success": False,
                "message": "Contact not found",
                "scanned": 0,
                "alerts_created": 0
            }

        # Verify ownership
        if contact.user_id != user_id:
            return {
                "success": False,
                "message": "Unauthorized access to contact",
                "scanned": 0,
                "alerts_created": 0
            }

        print(f"✅ Found contact: {contact.name}")

        # Detect platform
        from app.core.helpers.social_url_helper import SocialURLHelper

        platform = None
        if contact.linkedin_url:
            platform = "linkedin"
        elif contact.twitter_url:
            platform = "twitter"
        elif contact.social_handle:
            url_type = SocialURLHelper.detect_url_type(contact.social_handle)
            platform = url_type if url_type != "unknown" else None

        if not platform:
            return {
                "success": False,
                "message": "No valid social media URL found for this contact",
                "scanned": 0,
                "alerts_created": 0
            }

        print(f"🔀 Platform detected: {platform}")

        # Fetch posts based on platform
        posts = []
        sample_posts = []

        try:
            if platform == "linkedin":
                print(f"🚀 Fetching LinkedIn posts for {contact.name}...")
                linkedin_posts = await LazarusMonitoringService._fetch_linkedin_posts(
                    db, [contact]
                )
                if contact.focus_id in linkedin_posts:
                    posts = linkedin_posts[contact.focus_id]
                    # Add platform field and format author for frontend display
                    for post in posts:
                        post['platform'] = 'LinkedIn'
                        # Convert author object to string
                        if isinstance(post.get('author'), dict):
                            author_obj = post['author']
                            if 'name' in author_obj:
                                post['author'] = author_obj['name']
                            elif 'firstName' in author_obj and 'lastName' in author_obj:
                                post['author'] = f"{author_obj['firstName']} {author_obj['lastName']}"
                            else:
                                post['author'] = 'Unknown'
                        # Convert comments array to count
                        if isinstance(post.get('comments'), list):
                            post['comments'] = len(post['comments'])
                    sample_posts = posts[:3]  # First 3 for display
                    print(f"✅ Fetched {len(posts)} LinkedIn posts")

            elif platform == "twitter":
                print(f"🚀 Fetching Twitter posts for {contact.name}...")
                twitter_posts = await LazarusMonitoringService._fetch_twitter_posts(
                    db, [contact]
                )
                if contact.focus_id in twitter_posts:
                    posts = twitter_posts[contact.focus_id]
                    # Add platform field and ensure author is string
                    for post in posts:
                        post['platform'] = 'Twitter'
                        # Ensure author is string
                        if isinstance(post.get('author'), dict):
                            author_obj = post['author']
                            post['author'] = author_obj.get('username') or author_obj.get('name') or 'Unknown'
                    sample_posts = posts[:3]
                    print(f"✅ Fetched {len(posts)} tweets")

            # Analyze posts for buying signals
            alerts_created = 0
            alert_data = None
            scan_history_id = None
            scanned_posts_data = []

            # Import schemas for scan history (always needed, even with 0 posts)
            from app.domain.schemas.lazarus_schema import ScannedPost, ScanHistory

            if posts:
                # Deduplicate posts - remove posts we've already scanned
                # Get previously scanned post URLs from scan_history
                print(f"🔍 DEBUG: Checking for duplicate posts...")
                previously_scanned = await db["scan_history"].find(
                    {
                        "user_id": contact.user_id,
                        "source_id": contact.focus_id,
                        "source_type": LazarusMonitorTypeEnum.FOCUS_CONTACT
                    },
                    {"scanned_posts.post_url": 1, "scan_date": 1}
                ).sort("scan_date", -1).limit(10).to_list(10)  # Check last 10 scans

                print(f"🔍 DEBUG: Found {len(previously_scanned)} previous scans for this contact")

                scanned_urls = set()
                for scan in previously_scanned:
                    scan_date = scan.get("scan_date", "Unknown")
                    posts_in_scan = scan.get("scanned_posts", [])
                    print(f"🔍 DEBUG: Scan from {scan_date} had {len(posts_in_scan)} posts")
                    for post in posts_in_scan:
                        url = post.get("post_url")
                        if url:
                            # Normalize URL to remove tracking parameters before adding to set
                            normalized_url = LazarusMonitoringService._normalize_post_url(url)
                            scanned_urls.add(normalized_url)
                            # Show first 2 URLs in full to compare
                            if len(scanned_urls) <= 2:
                                print(f"🔍 DEBUG:   - Scanned URL (normalized, len={len(normalized_url)}): {normalized_url}")

                print(f"🔍 DEBUG: Total unique previously scanned URLs: {len(scanned_urls)}")

                # Debug current posts
                print(f"🔍 DEBUG: Current posts before deduplication: {len(posts)}")
                for i, p in enumerate(posts[:3]):  # Show first 3
                    current_url = p.get("url") or p.get("postUrl") or p.get("tweet_url") or p.get("link")
                    normalized_current = LazarusMonitoringService._normalize_post_url(current_url) if current_url else None
                    is_duplicate = normalized_current in scanned_urls if normalized_current else False
                    print(f"🔍 DEBUG:   Post {i+1} URL (normalized, len={len(normalized_current) if normalized_current else 0}): {normalized_current}")
                    print(f"🔍 DEBUG:   Post {i+1} is_duplicate: {is_duplicate}")

                # Filter out duplicate posts - normalize URLs before comparison
                original_count = len(posts)
                posts = [
                    p for p in posts
                    if LazarusMonitoringService._normalize_post_url(
                        p.get("url") or p.get("postUrl") or p.get("tweet_url") or p.get("link")
                    ) not in scanned_urls
                ]

                if original_count > len(posts):
                    print(f"🔄 Filtered out {original_count - len(posts)} duplicate posts (already scanned)")

                if not posts:
                    print(f"📭 No new posts to analyze (all {original_count} posts were already scanned)")

            if posts:
                print(f"🤖 Analyzing {len(posts)} posts with AI...")

                # Build scanned_posts array for saving (regardless of signal detection)
                scanned_posts_data = []

                for i, post in enumerate(posts[:10]):  # Save up to 10 posts
                    post_url = post.get("url") or post.get("postUrl") or post.get("tweet_url") or post.get("link")
                    post_text = post.get("text") or post.get("content")

                    if post_url and post_text:
                        scanned_posts_data.append({
                            "post_url": post_url,
                            "post_text": post_text,
                            "post_platform": "LinkedIn" if platform == "linkedin" else "Twitter",
                            "post_author": (
                                post.get("author", {}).get("name") if isinstance(post.get("author"), dict) and platform == "linkedin"
                                else post.get("author", {}).get("username") if isinstance(post.get("author"), dict)
                                else post.get("author")
                            ),
                            "post_created_at": post.get("created_at") or post.get("postedAt") or post.get("createdAt"),
                            "post_likes": post.get("likes") or post.get("numLikes") or post.get("likeCount") or 0,
                            "post_comments": post.get("comments") or post.get("numComments") or post.get("replyCount") or 0,
                            "post_index": i
                        })

                # Use the correct analysis method based on platform
                if platform == "linkedin":
                    analysis_result = await LazarusMonitoringService._analyze_focus_contact(
                        db, contact, [], posts  # Empty tweets list, LinkedIn posts
                    )
                else:
                    analysis_result = await LazarusMonitoringService._analyze_focus_contact(
                        db, contact, posts, []  # Tweets, empty LinkedIn list
                    )

                # Save scan history REGARDLESS of signal detection
                try:
                    # Determine if signal was detected
                    signal_detected = analysis_result and analysis_result.get('signal_detected', bool(analysis_result.get('alert_id')))

                    scan_history = ScanHistory(
                        user_id=contact.user_id,
                        source_type=LazarusMonitorTypeEnum.FOCUS_CONTACT,
                        source_id=contact.focus_id,
                        source_name=contact.name,
                        scan_date=datetime.utcnow(),
                        platform="LinkedIn" if platform == "linkedin" else "Twitter",
                        posts_scanned_count=len(scanned_posts_data),
                        scanned_posts=scanned_posts_data,
                        signal_detected=signal_detected,
                        alert_id=analysis_result.get('alert_id') if analysis_result else None,
                        signal_type=analysis_result.get('evidence', {}).get('signal_type') if analysis_result and analysis_result.get('evidence') else None,
                        confidence=analysis_result.get('evidence', {}).get('confidence') if analysis_result and analysis_result.get('evidence') else (analysis_result.get('confidence') if analysis_result else None),
                        triggering_post_index=analysis_result.get('evidence', {}).get('triggering_post_index') if analysis_result and analysis_result.get('evidence') else None,
                        rejection_reason=analysis_result.get('rejection_reason') if analysis_result and not signal_detected else None,
                    )

                    result = await db["scan_history"].insert_one(scan_history.dict(by_alias=True))
                    scan_history_id = str(result.inserted_id)
                    print(f"📋 Saved scan history with {len(scanned_posts_data)} posts (scan_id: {scan_history_id})")

                    # Debug: Show first few URLs being saved
                    if scanned_posts_data:
                        print(f"🔍 DEBUG: Saving post URLs to scan_history:")
                        for i, sp in enumerate(scanned_posts_data[:2]):
                            url = sp.get('post_url', 'NO URL')
                            print(f"🔍 DEBUG:   Post {i+1} (len={len(url) if url != 'NO URL' else 0}): {url}")

                except Exception as e:
                    logger.error(f"Failed to save scan history: {str(e)}")
                    print(f"⚠️  Failed to save scan history: {str(e)}")

                if analysis_result:
                    # Check for duplicate alerts (same contact, same alert type, same content, within last 7 days)
                    seven_days_ago = datetime.utcnow() - timedelta(days=7)

                    # Get the evidence text from the new alert
                    new_evidence_text = analysis_result.get('evidence', {}).get('evidence_text', '')

                    existing_alert = await db["lazarus_alerts"].find_one({
                        "user_id": contact.user_id,
                        "source_id": contact.focus_id,
                        "alert_type": analysis_result.get('alert_type'),
                        "status": {"$in": [LazarusAlertStatusEnum.NEW, LazarusAlertStatusEnum.VIEWED]},
                        "created_at": {"$gte": seven_days_ago},
                        "evidence.evidence_text": new_evidence_text  # Check actual post content
                    })

                    if existing_alert:
                        print(f"ℹ️  Duplicate alert detected - same content already alerted")
                        print(f"   Existing alert from: {existing_alert.get('created_at')}")
                        print(f"   Evidence: {new_evidence_text[:100]}...")
                        # Still prepare alert data for frontend display
                        alert_data = {
                            "alert_type": analysis_result.get('alert_type'),
                            "alert_message": "Alert already exists (duplicate detected)",
                            "suggested_pitch": analysis_result.get('suggested_pitch'),
                            "confidence": analysis_result.get('evidence', {}).get('confidence'),
                            "signal_type": analysis_result.get('evidence', {}).get('signal_type')
                        }
                    else:
                        # Save the alert to database
                        try:
                            alert = LazarusAlert(**analysis_result)
                            await db["lazarus_alerts"].insert_one(alert.dict(by_alias=True))
                            alerts_created = 1

                            # Update scan_history with alert_id
                            if scan_history_id:
                                await db["scan_history"].update_one(
                                    {"_id": scan_history_id},
                                    {"$set": {"alert_id": analysis_result.get('alert_id')}}
                                )

                            # Prepare alert data for frontend display
                            alert_data = {
                                "alert_type": analysis_result.get('alert_type'),
                                "alert_message": analysis_result.get('alert_message'),
                                "suggested_pitch": analysis_result.get('suggested_pitch'),
                                # Extract confidence from evidence if available
                                "confidence": analysis_result.get('evidence', {}).get('confidence'),
                                "signal_type": analysis_result.get('evidence', {}).get('signal_type')
                            }

                            print(f"🎯 Buying signal detected and alert created!")
                            print(f"   Alert Type: {analysis_result.get('alert_type')}")
                            print(f"   Alert Message: {analysis_result.get('alert_message')}")
                            print(f"   Suggested Pitch: {analysis_result.get('suggested_pitch', 'N/A')[:100]}...")

                            # Auto-enrich contact if alert created and not already enriched
                            if contact.linkedin_url and not contact.enriched_at:
                                print(f"🔍 Auto-enriching contact after alert creation...")
                                await LazarusMonitoringService._auto_enrich_contact(db, contact)

                        except Exception as e:
                            logger.error(f"Failed to create alert: {str(e)}")
                            print(f"❌ Failed to create alert: {str(e)}")
                else:
                    print(f"ℹ️  No buying signals detected")

            # Update scan timestamps and alert count
            scan_date = datetime.utcnow()
            next_scan = scan_date + timedelta(days=contact.scan_frequency_days)
            await LazarusRepository.update_focus_contact(
                db, focus_id, user_id, {
                    "last_scan_date": scan_date,
                    "next_scan_date": next_scan,
                    "scan_count": contact.scan_count + 1,
                    "alert_count": contact.alert_count + alerts_created
                }
            )

            result = {
                "success": True,
                "message": f"Scanned {contact.name} successfully",
                "scanned": 1,
                "alerts_created": alerts_created,
                "sample_posts": sample_posts,
                "platform": platform
            }

            # Add alert data if available
            if alert_data:
                result["alert_data"] = alert_data

            return result

        except Exception as e:
            logger.error(f"Error scanning contact {focus_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Scan failed: {str(e)}",
                "scanned": 0,
                "alerts_created": 0
            }

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

            # Detect expansion (new offices, market entry)
            expansion_alert = await LazarusMonitoringService._detect_expansion(
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
            for alert in [hiring_alert, cash_alert, expansion_alert, pivot_alert, dead_alert]:
                if alert:
                    # Calculate priority score
                    alert_dict = alert.dict() if hasattr(alert, 'dict') else alert
                    priority_score, priority_level = LazarusMonitoringService.calculate_priority_score(alert_dict)
                    alert_dict["priority_score"] = priority_score
                    alert_dict["priority_level"] = priority_level

                    await LazarusRepository.create_alert(db, alert_dict)
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
    async def _detect_expansion(
        db: AsyncIOMotorDatabase, monitor: CompanyMonitor
    ) -> Optional[Dict[str, Any]]:
        """
        Detect company expansion via Google News
        Triggers on: new office openings, market entry, geographic expansion
        """
        try:
            google_service = ApifyGoogleSearchService()

            # Build dork query for expansion signals
            dork_query = f'"{monitor.company_name}" ("expanding" OR "new office" OR "opening in" OR "expansion" OR "entering market" OR "opens new")'

            logger.info(f"🔍 Searching for expansion signals: {dork_query}")

            country_code = monitor.country_code if hasattr(monitor, 'country_code') and monitor.country_code else "us"

            results = await google_service.search(
                dork_query=dork_query,
                max_results=10,
                country_code=country_code
            )

            # Look for recent expansion news (within 30 days)
            if results and len(results) > 0:
                recent_news = [r for r in results if r.source_date and
                               (datetime.utcnow() - r.source_date.replace(tzinfo=None)).days <= 30]

                if recent_news:
                    news_item = recent_news[0]

                    logger.info(f"📈 EXPANSION DETECTED: {monitor.company_name} - {news_item.title}")

                    return {
                        "alert_id": str(uuid.uuid4()),
                        "user_id": monitor.user_id,
                        "source_type": LazarusMonitorTypeEnum.COMPANY,
                        "source_id": monitor.monitor_id,
                        "alert_type": LazarusAlertTypeEnum.EXPANSION,
                        "alert_message": f"Growth Alert: {monitor.company_name} is expanding operations",
                        "evidence": {
                            "detected_date": datetime.utcnow().isoformat(),
                            "signal_source": f"Google News - {news_item.url}",
                            "old_value": None,
                            "new_value": news_item.title,
                            "tweets": [news_item.snippet],
                            "signal_type": "expansion",
                            "confidence": 0.85
                        },
                        "suggested_pitch": f"Congratulations on {monitor.company_name}'s expansion! Growing teams often need solutions like ours - let's chat.",
                        "status": LazarusAlertStatusEnum.NEW,
                        "resurrected_lead_id": monitor.source_lead_id,
                        "created_date": datetime.utcnow(),
                        "last_updated": datetime.utcnow(),
                    }

            return None

        except Exception as e:
            logger.error(f"Error detecting expansion for {monitor.company_name}: {str(e)}")
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
