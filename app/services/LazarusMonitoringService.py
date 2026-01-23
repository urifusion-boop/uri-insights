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
from app.services.ApifyLinkedInPostScraperService import ApifyLinkedInPostScraperService
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

            # Use ApifyLinkedInPostScraperService to fetch posts
            linkedin_service = ApifyLinkedInPostScraperService()
            result = await linkedin_service.fetch_linkedin_posts(
                linkedin_urls=linkedin_urls,
                deep_scrape=True,
                limit_per_source=10  # 10 posts per contact (2-4 weeks of activity)
            )

            if not result.get("success"):
                logger.warning(f"LinkedIn post fetch failed: {result.get('error_message', 'Unknown error')}")
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

            # Collect handles and keywords
            handles = [c.twitter_url.split('/')[-1] if c.twitter_url else c.social_handle.split('/')[-1]
                      for c in contacts_with_twitter if c.twitter_url or c.social_handle]

            all_keywords = []
            for contact in contacts_with_twitter:
                all_keywords.extend(contact.industry_keywords)

            # Fetch using batch method
            tweets = await LazarusMonitoringService._fetch_batch_tweets(db, handles, all_keywords)

            # Map tweets back to contacts by focus_id
            posts_by_focus_id = {}
            for contact in contacts_with_twitter:
                handle = contact.twitter_url.split('/')[-1] if contact.twitter_url else contact.social_handle.split('/')[-1]
                contact_tweets = [t for t in tweets if t.get("handle") == handle]

                if contact_tweets:
                    posts_by_focus_id[contact.focus_id] = contact_tweets
                    print(f"✅ Found {len(contact_tweets)} tweets for {contact.name}")

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
        # Default to all signal types if no settings found
        user_signal_preferences = ["pain", "switch", "hiring", "funding"]

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

            if signal_analysis:
                print(f"🎯 SIGNAL DETECTED!")
                print(f"   Type: {signal_analysis.get('signal_type')}")
                print(f"   Confidence: {signal_analysis.get('confidence')}")
                print(f"   Evidence: {signal_analysis.get('evidence', '')[:200]}...")
                # Map signal_type to alert_type
                signal_type_map = {
                    "pain": LazarusAlertTypeEnum.BUYING_INTENT,
                    "switch": LazarusAlertTypeEnum.BUYING_INTENT,
                    "hiring": LazarusAlertTypeEnum.HIRING_SPREE,
                    "funding": LazarusAlertTypeEnum.CASH_INJECTION,
                }

                alert_type = signal_type_map.get(
                    signal_analysis.get("signal_type", "pain"),
                    LazarusAlertTypeEnum.BUYING_INTENT
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
                        # Platform-agnostic fields
                        "post_text": signal_analysis.get("evidence"),
                        "post_platform": primary_platform,
                        # Legacy field for backward compatibility
                        "tweet_text": signal_analysis.get("evidence"),
                    },
                    "suggested_pitch": suggested_pitch,
                    "status": LazarusAlertStatusEnum.NEW,
                    "source_lead_id": contact.source_lead_id,
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
        prompt = LazarusPrompt.ANALYZE_BUYING_SIGNALS.value.format(
            contact_name=contact.name,
            current_company=contact.current_company or "Unknown",
            keywords=", ".join(contact.industry_keywords),
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

            # Only return if signal detected with high confidence
            if result.signal_detected and result.confidence >= 0.7:
                return {
                    "signal_type": result.signal_type,
                    "confidence": result.confidence,
                    "evidence": result.evidence,
                    "reason": result.reason
                }

        except Exception as e:
            logger.error(f"AI buying intent detection failed: {e}")
            # Fallback to simple keyword matching if AI fails
            return await LazarusMonitoringService._fallback_keyword_detection(
                tweets, linkedin_posts, contact.industry_keywords
            )

        return None

    @staticmethod
    async def _fallback_keyword_detection(
        tweets: List[Dict[str, Any]],
        linkedin_posts: List[Dict[str, Any]],
        keywords: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Fallback: Simple keyword matching if AI fails"""
        buying_signals = ["looking for", "need", "recommend", "anyone know", "suggestions",
                         "alternative", "switch", "considering", "evaluate"]

        # Check both tweets and LinkedIn posts
        all_content = tweets + linkedin_posts

        for item in all_content:
            text = item.get("text", "").lower()
            for keyword in keywords:
                if keyword.lower() in text:
                    if any(signal in text for signal in buying_signals):
                        return {
                            "signal_type": "switch",
                            "confidence": 0.6,
                            "evidence": text[:200],
                            "reason": "Keyword match with buying signal phrase"
                        }
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
            prompt = LazarusPrompt.GENERATE_PITCH.value.format(
                contact_name=contact.name,
                current_company=contact.current_company or "their company",
                signal_type=signal_analysis.get("signal_type", "unknown"),
                evidence=signal_analysis.get("evidence", ""),
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
            if posts:
                print(f"🤖 Analyzing {len(posts)} posts with AI...")

                # Use the correct analysis method based on platform
                if platform == "linkedin":
                    analysis_result = await LazarusMonitoringService._analyze_focus_contact(
                        db, contact, [], posts  # Empty tweets list, LinkedIn posts
                    )
                else:
                    analysis_result = await LazarusMonitoringService._analyze_focus_contact(
                        db, contact, posts, []  # Tweets, empty LinkedIn list
                    )

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
