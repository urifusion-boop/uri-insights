"""
ConversationalLeadJobService.py
Background job service for fetching leads from Twitter, Facebook, and TikTok
when a conversational lead form is created or updated.
"""
import asyncio
import time
import re
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.OpenAIApifyTwitterService import OpenAIApifyTwitterService
from app.services.OpenAIApifyFacebookService import OpenAIApifyFacebookService
from app.services.OpenAIApifyTiktokService import OpenAIApifyTiktokService
from app.services.IntentAnalysisService import IntentAnalysisService, CategoryConfig
from app.services.uri_microservices.UriBackendService import UriBackendService
from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService
from app.repository.LeadRepository import LeadRepository
from app.repository.LeadSearchHistoryRepository import LeadSearchHistoryRepository
from app.domain.schemas.lead_schema import LeadCreate
from app.domain.enums.endpoints_enum import EndpointsEnum
from app.domain.schemas.lead_search_history_schema import LeadSearchHistoryCreate, SearchResultStats
from app.domain.enums.lead_enum import LeadSourceEnum, LeadStatusEnum, LeadOpportunityTypeEnum, IntentCategoryEnum, SentimentTypeEnum
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.domain.schemas.browsercloud_schema import BrowsercloudPlatformEnum


class ContentDeduplicator:
    """
    Handles content-based deduplication to detect retweets, shares, and reposts.
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text by removing URLs, mentions, hashtags, emojis, and extra whitespace.
        This helps identify duplicate content even when URLs/usernames differ.
        """
        if not text:
            return ""

        # Convert to lowercase
        normalized = text.lower()

        # Remove URLs
        normalized = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', normalized)

        # Remove mentions (@username)
        normalized = re.sub(r'@\w+', '', normalized)

        # Remove hashtags (#hashtag)
        normalized = re.sub(r'#\w+', '', normalized)

        # Remove emojis and special characters (keep only alphanumeric and basic punctuation)
        normalized = re.sub(r'[^\w\s.,!?-]', '', normalized)

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    @staticmethod
    def generate_content_hash(text: str) -> str:
        """
        Generate a SHA-256 hash of normalized text for deduplication.
        Returns first 16 characters of hash for efficient storage/comparison.
        """
        normalized = ContentDeduplicator.normalize_text(text)
        if not normalized:
            return ""

        # Generate SHA-256 hash
        hash_obj = hashlib.sha256(normalized.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # Use first 16 chars for efficiency


class PlatformKeywordOptimizer:
    """
    Optimizes keywords for different social media platforms.
    Each platform has unique search behaviors and best practices.
    """

    @staticmethod
    def optimize_for_twitter(keyword: str) -> str:
        """
        Twitter optimization: Keep keywords natural for best platform API matching

        No transformation needed - Twitter's search API handles fuzzy matching,
        synonyms, and relevance ranking automatically. Natural keywords yield
        better results than forced question formats.

        Examples:
        - "laptop repair" → "laptop repair"
        - "struggling with brand identity" → "struggling with brand identity"
        - "broken screen" → "broken screen"
        """
        return keyword.strip()

    @staticmethod
    def optimize_for_facebook(keyword: str) -> str:
        """
        Facebook optimization: Keep keywords natural for best platform API matching

        No transformation needed - Facebook's search API handles natural language,
        fuzzy matching, and relevance ranking automatically. Natural keywords yield
        better results than forced prefixes.

        Examples:
        - "laptop repair" → "laptop repair"
        - "struggling with brand identity" → "struggling with brand identity"
        - "broken screen" → "broken screen"
        """
        return keyword.strip()

    @staticmethod
    def optimize_for_tiktok(keyword: str) -> str:
        """
        TikTok optimization: Convert to hashtag format

        Examples:
        - "laptop" → "#laptop"
        - "affordable laptop" → "#affordablelaptop"
        - "laptop in lagos" → "#laptopinlagos"
        """
        keyword_lower = keyword.lower().strip()

        # If already has hashtag, keep as-is
        if keyword_lower.startswith("#"):
            return keyword

        # Remove spaces and special chars, create hashtag
        hashtag = keyword_lower.replace(" ", "").replace("-", "").replace("_", "")
        return f"#{hashtag}"


class ConversationalLeadJobService:
    """
    Service to handle background jobs for fetching conversational leads
    from multiple social media platforms.
    """

    @staticmethod
    async def fetch_leads_from_platforms(
        db: AsyncIOMotorDatabase,
        lead_form: Dict,
        user_id: str,
        job_id: str = None
    ) -> Dict:
        """
        Fetch leads from all enabled platforms in the lead form configuration.
        This runs as a background job immediately after form save/update.

        Args:
            db: MongoDB database instance
            lead_form: The lead form document containing platform configs and keywords
            user_id: User ID to assign leads to
            job_id: Optional job ID for tracking progress (for async polling)

        Returns:
            Dict with statistics: total_fetched, total_qualified, new_leads_saved, duplicates_skipped
        """
        from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository

        stats = {
            "total_fetched": 0,
            "total_qualified": 0,
            "new_leads_saved": 0,
            "duplicates_skipped": 0
        }

        # Track start time for duration
        start_time = time.time()
        search_success = True
        error_msg = None

        # Helper function to update job progress
        async def update_progress(progress: int, message: str):
            if job_id:
                await LeadGenerationJobRepository.update_job(
                    db=db,
                    job_id=job_id,
                    progress=progress,
                    message=message
                )

        try:
            print(f"🚀 BACKGROUND JOB STARTED: Fetching leads for form {lead_form.get('lead_form_id')}")
            print(f"   Platform configs: {lead_form.get('platform_configs', [])}")
            print(f"   Keywords: {lead_form.get('keywords', [])}")
        except Exception as log_error:
            print(f"Error in initial logging: {str(log_error)}")

        try:
            platform_configs = lead_form.get("platform_configs", [])
            keywords = lead_form.get("keywords", [])
            implied_keywords = lead_form.get("implied_keywords", [])

            # Combine direct and implied keywords for comprehensive search
            all_search_keywords = keywords + (implied_keywords or [])

            if not all_search_keywords or len(all_search_keywords) == 0:
                print(f"No keywords provided for lead form {lead_form.get('lead_form_id')}")
                return stats

            print(f"🔍 Search keywords: {len(keywords)} direct + {len(implied_keywords or [])} implied = {len(all_search_keywords)} total")

            # Collect all enabled platforms (normalize to lowercase for comparison)
            enabled_platforms = {
                config.get("platform").lower(): config
                for config in platform_configs
                if config.get("enabled", False) and config.get("platform")
            }

            if not enabled_platforms:
                print(f"No enabled platforms for lead form {lead_form.get('lead_form_id')}")
                return

            all_leads: List[LeadCreate] = []

            print(f"📋 Enabled platforms: {list(enabled_platforms.keys())}")
            print(f"   Checking for Twitter: '{BrowsercloudPlatformEnum.TWITTER.value}'")
            print(f"   Checking for Facebook: '{BrowsercloudPlatformEnum.FACEBOOK.value}'")
            print(f"   Checking for TikTok: '{BrowsercloudPlatformEnum.TIKTOK.value}'")

            # MULTI-KEYWORD STRATEGY - Mix direct and implied keywords with smart prioritization
            # Strategy: Use 8 keywords total - 4 direct + 4 implied
            # Each group: 2 multi-word (3+) + 2 two-word keywords for optimal specificity
            buying_signals = lead_form.get("buying_signals", [])
            prioritized_keywords = []

            def select_keywords_by_word_count(keyword_list, target_count=4):
                """
                Select keywords with optimal word count distribution:
                - Prefer 2 keywords with 3+ words (most specific)
                - Then 2 keywords with exactly 2 words

                Returns list of selected keywords
                """
                if not keyword_list:
                    return []

                # Separate keywords by word count
                three_plus_words = [k for k in keyword_list if len(k.split()) >= 3]
                two_words = [k for k in keyword_list if len(k.split()) == 2]
                one_word = [k for k in keyword_list if len(k.split()) == 1]

                # Sort each group by word count (descending) for tie-breaking
                three_plus_words.sort(key=lambda k: len(k.split()), reverse=True)

                selected = []

                # Priority 1: Get 2 keywords with 3+ words
                selected.extend(three_plus_words[:2])

                # Priority 2: Get 2 keywords with 2 words
                if len(selected) < target_count and two_words:
                    selected.extend(two_words[:2])

                # Fallback: If we don't have enough, fill with what's available
                if len(selected) < target_count:
                    # Add more 3+ word keywords if available
                    if len(three_plus_words) > 2:
                        remaining = target_count - len(selected)
                        selected.extend(three_plus_words[2:2+remaining])

                    # Still short? Add more 2-word keywords
                    if len(selected) < target_count and len(two_words) > 2:
                        remaining = target_count - len(selected)
                        selected.extend(two_words[2:2+remaining])

                    # Still short? Add 1-word keywords as last resort
                    if len(selected) < target_count and one_word:
                        remaining = target_count - len(selected)
                        selected.extend(one_word[:remaining])

                return selected[:target_count]  # Ensure we don't exceed target

            # Build prioritized keyword list (8 KEYWORDS: 4 direct + 4 implied)
            # 1. Add 4 direct keywords (2 with 3+ words, 2 with 2 words)
            if keywords and len(keywords) > 0:
                direct_selected = select_keywords_by_word_count(keywords, target_count=4)
                prioritized_keywords.extend(direct_selected)
                print(f"   📝 Direct keywords selected: {direct_selected}")

            # 2. Add 4 implied keywords (2 with 3+ words, 2 with 2 words)
            if implied_keywords and len(implied_keywords) > 0:
                implied_selected = select_keywords_by_word_count(implied_keywords, target_count=4)
                prioritized_keywords.extend(implied_selected)
                print(f"   📝 Implied keywords selected: {implied_selected}")

            # 3. Fallback: If we still don't have 8 keywords, use buying signals
            if len(prioritized_keywords) < 8 and buying_signals and len(buying_signals) > 0:
                remaining_slots = 8 - len(prioritized_keywords)
                signal_selected = select_keywords_by_word_count(buying_signals, target_count=remaining_slots)
                prioritized_keywords.extend(signal_selected)
                print(f"   📝 Buying signal keywords selected: {signal_selected}")

            if not prioritized_keywords:
                print(f"⚠️ No keywords available for search")
                return stats

            print(f"🎯 Prioritized keywords (8 total: 4 direct + 4 implied): {prioritized_keywords}")

            # Build category configuration once (used for intent analysis)
            category_config = ConversationalLeadJobService._build_category_config(lead_form)

            # Get custom scoring thresholds if specified
            scoring_thresholds = lead_form.get("scoring_thresholds", {})
            intent_min = scoring_thresholds.get("intent_score_min", 0.50)
            relevance_min = scoring_thresholds.get("relevance_score_min", 0.45)
            final_min = scoring_thresholds.get("final_score_min", 0.55)

            # Update progress: Starting keyword search
            await update_progress(10, f"Searching with {len(prioritized_keywords)} keyword(s) across {len(enabled_platforms)} platform(s)...")

            # Try ALL keywords to maximize qualified leads (no early stopping)
            qualified_leads = []
            for keyword_idx, keyword in enumerate(prioritized_keywords, 1):
                print(f"\n🔍 KEYWORD ATTEMPT {keyword_idx}/{len(prioritized_keywords)}: '{keyword}'")
                progress_percent = 10 + (keyword_idx * 20)  # 10, 30, 50
                await update_progress(progress_percent, f"Fetching from platforms with keyword '{keyword}'...")

                # CONCURRENT FETCHING: Optimize keywords per platform and fetch in parallel
                fetch_tasks = []
                platform_timeout = 45  # 45 seconds per platform

                if BrowsercloudPlatformEnum.TWITTER.value in enabled_platforms:
                    twitter_keyword = PlatformKeywordOptimizer.optimize_for_twitter(keyword)
                    print(f"   🐦 Twitter: '{twitter_keyword}'")
                    fetch_tasks.append(
                        asyncio.wait_for(
                            ConversationalLeadJobService._fetch_twitter_leads(
                                twitter_keyword, user_id, lead_form.get("lead_form_id")
                            ),
                            timeout=platform_timeout
                        )
                    )

                if BrowsercloudPlatformEnum.FACEBOOK.value in enabled_platforms:
                    facebook_keyword = PlatformKeywordOptimizer.optimize_for_facebook(keyword)
                    print(f"   📘 Facebook: '{facebook_keyword}'")
                    fetch_tasks.append(
                        asyncio.wait_for(
                            ConversationalLeadJobService._fetch_facebook_leads(
                                facebook_keyword, user_id, lead_form.get("lead_form_id")
                            ),
                            timeout=platform_timeout
                        )
                    )

                if BrowsercloudPlatformEnum.TIKTOK.value in enabled_platforms:
                    tiktok_keyword = PlatformKeywordOptimizer.optimize_for_tiktok(keyword)
                    print(f"   🎵 TikTok: '{tiktok_keyword}'")
                    fetch_tasks.append(
                        asyncio.wait_for(
                            ConversationalLeadJobService._fetch_tiktok_leads(
                                tiktok_keyword, user_id, lead_form.get("lead_form_id")
                            ),
                            timeout=platform_timeout
                        )
                    )

                # Execute all fetch tasks concurrently
                keyword_leads = []
                if fetch_tasks:
                    print(f"   ⚡ Fetching from {len(fetch_tasks)} platform(s) concurrently...")
                    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                    # Collect successful results
                    for idx, result in enumerate(results):
                        if isinstance(result, asyncio.TimeoutError):
                            print(f"   ⏱️ Platform {idx+1} timed out after {platform_timeout}s")
                        elif isinstance(result, Exception):
                            print(f"   ❌ Platform {idx+1} error: {str(result)}")
                        elif isinstance(result, list):
                            keyword_leads.extend(result)
                            print(f"   ✅ Platform {idx+1} returned {len(result)} leads")

                all_leads.extend(keyword_leads)
                print(f"   📊 Fetched {len(keyword_leads)} raw leads for keyword '{keyword}'")

                # Analyze leads from this keyword
                if keyword_leads:
                    keyword_qualified = await ConversationalLeadJobService._analyze_and_filter_leads(
                        keyword_leads, category_config, intent_min, relevance_min, final_min
                    )
                    qualified_leads.extend(keyword_qualified)
                    print(f"   ✅ {len(keyword_qualified)} qualified from this keyword")
                    print(f"   📈 TOTAL QUALIFIED SO FAR: {len(qualified_leads)}")

                # Continue with all keywords to maximize results (no early stopping)

            # Update statistics
            stats["total_fetched"] = len(all_leads)
            stats["total_qualified"] = len(qualified_leads)
            print(f"\n✅ INTENT ANALYSIS COMPLETE: {len(qualified_leads)}/{len(all_leads)} leads qualified")

            # Update progress: Analyzing complete, now saving
            await update_progress(80, f"Analyzed {len(all_leads)} posts, saving {len(qualified_leads)} qualified leads...")

            # Save only qualified leads to database
            if qualified_leads:
                save_result = await ConversationalLeadJobService._save_leads_batch(db, qualified_leads)
                new_count = save_result.get("successful_count", 0)
                duplicate_count = save_result.get("skipped_duplicates", 0)

                stats["new_leads_saved"] = new_count
                stats["duplicates_skipped"] = duplicate_count

                if new_count > 0 and duplicate_count > 0:
                    print(f"✅ Saved {new_count} new leads, {duplicate_count} duplicates skipped")
                elif new_count > 0:
                    print(f"✅ Successfully saved {new_count} qualified leads from {len(enabled_platforms)} platform(s)")
                elif duplicate_count > 0:
                    print(f"ℹ️ All {duplicate_count} qualified leads were already in your database")
                else:
                    print(f"No new leads saved")

                if new_count > 0:
                    try:
                        limit_available, current_count = await UriTaskManagerService.get_elapsed_leads_limit_and_count(user_id)
                        await UriTaskManagerService.update_user_feature_limit_specific_limit(
                            user_id=user_id,
                            url_path=EndpointsEnum.LEAD_GEN.value,
                            count=new_count + current_count,
                        )
                    except Exception as e:
                        print(f"Failed to update feature limit after conversational leads: {str(e)}")
            else:
                print(f"No qualified leads found after intent analysis")

        except Exception as e:
            import traceback
            print(f"❌ ERROR in fetch_leads_from_platforms: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            search_success = False
            error_msg = str(e)
            # Update job with error status
            if job_id:
                await LeadGenerationJobRepository.update_job(
                    db=db,
                    job_id=job_id,
                    status="failed",
                    progress=0,
                    error=str(e)
                )
            # Don't raise - this is a background job, we just log the error

        # Calculate duration
        duration = time.time() - start_time

        # Save search history
        try:
            search_history = LeadSearchHistoryCreate(
                user_id=user_id,
                lead_form_id=lead_form.get("lead_form_id", ""),
                lead_form_name=lead_form.get("form_title", ""),
                keyword=", ".join(all_search_keywords[:3]) + ("..." if len(all_search_keywords) > 3 else ""),  # Show first 3 keywords # type: ignore
                platforms=list(enabled_platforms.keys()),  # Convert dict keys to list
                results=SearchResultStats(**stats),
                duration_seconds=round(duration, 2),
                success=search_success,
                error_message=error_msg
            )

            await LeadSearchHistoryRepository.create(db, search_history)
            print(f"📝 Search history saved: {stats['new_leads_saved']} new, {stats['duplicates_skipped']} duplicates")
        except Exception as history_error:
            print(f"⚠️ Failed to save search history: {str(history_error)}")
            # Don't fail the entire operation if history save fails

        # Track trial usage if leads were generated
        if stats['new_leads_saved'] > 0:
            try:
                await UriBackendService.increment_trial_usage(
                    user_id=user_id,
                    field='trialLeadsGenerated',
                    amount=stats['new_leads_saved']
                )
                print(f"📊 Trial usage tracked: {stats['new_leads_saved']} leads")
            except Exception as usage_error:
                print(f"⚠️ Failed to track trial usage: {str(usage_error)}")
                # Don't fail the entire operation if usage tracking fails

        # Update job with final status
        if job_id:
            if search_success:
                message = "Lead fetching and intent analysis completed successfully"
                if stats["new_leads_saved"] > 0 and stats["duplicates_skipped"] > 0:
                    message = f"Found {stats['new_leads_saved']} new leads. {stats['duplicates_skipped']} duplicates were already in your database."
                elif stats["new_leads_saved"] > 0:
                    message = f"Successfully found {stats['new_leads_saved']} new leads!"
                elif stats["duplicates_skipped"] > 0:
                    message = f"No new leads found. All {stats['duplicates_skipped']} qualified leads were already in your database."
                elif stats["total_qualified"] == 0 and stats["total_fetched"] > 0:
                    message = f"Analyzed {stats['total_fetched']} posts but none matched your criteria."
                elif stats["total_fetched"] == 0:
                    message = "No posts found matching your keywords."

                await LeadGenerationJobRepository.update_job(
                    db=db,
                    job_id=job_id,
                    status="completed",
                    progress=100,
                    message=message,
                    stats=stats
                )
                print(f"✅ Job {job_id} completed: {message}")
            else:
                print(f"❌ Job {job_id} failed with error: {error_msg}")

        return stats

    @staticmethod
    async def _fetch_twitter_leads(
        search_query: str,
        user_id: str,
        lead_form_id: Optional[str] = None
    ) -> List[LeadCreate]:
        """Fetch leads from Twitter using Apify with smart search query"""
        try:
            print(f"🐦 Fetching Twitter leads with search query: '{search_query}'")
            twitter_service = OpenAIApifyTwitterService()
            response = await twitter_service.fetch_tweets_with_analysis(search_query, max_tweets=25, analyze_sentiment=False)
            print(f"   Twitter API response success: {response.get('success')}")
            tweets = response.get("tweets", [])
            print(f"   Found {len(tweets)} tweets")

            leads = []
            for tweet in tweets:
                tweet_text = tweet.get("text", "")
                lead = LeadCreate(
                    first_name=tweet.get("author", "Twitter User"),
                    last_name="",
                    username=tweet.get("author", ""),
                    mention=tweet_text,
                    lead_reason=tweet_text,
                    lead_status=LeadStatusEnum.NEW,
                    opportunity_type=LeadOpportunityTypeEnum.OTHER,
                    tags=[],
                    twitter_url=tweet.get("url", ""),
                    lead_link=tweet.get("url", ""),
                    social_profile_link=tweet.get("url", ""),
                    picture_url="",
                    created_date=ConversationalLeadJobService._convert_twitter_date(
                        tweet.get("created_at", "")
                    ),
                    last_updated=ConversationalLeadJobService._convert_twitter_date(
                        tweet.get("created_at", "")
                    ),
                    lead_type=LeadFormTypeEnum.CONVERSATIONAL,
                    website_url=tweet.get("url", ""),
                    lead_source=LeadSourceEnum.X,
                    assigned_to=user_id,
                    starred=False,
                    lead_form_snapshot_id=lead_form_id,
                    content_hash=ContentDeduplicator.generate_content_hash(tweet_text),
                )

                # Add sentiment and confidence if available
                if "sentiment" in tweet:
                    lead.notes = f"Sentiment: {tweet['sentiment']}"
                if "confidence" in tweet:
                    lead.score = int(float(tweet.get("confidence", 0)) * 100)

                leads.append(lead)

            return leads
        except Exception as e:
            print(f"❌ Error fetching Twitter leads: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    async def _fetch_facebook_leads(
        search_query: str,
        user_id: str,
        lead_form_id: Optional[str] = None
    ) -> List[LeadCreate]:
        """Fetch leads from Facebook using Apify with smart search query"""
        try:
            print(f"📘 Fetching Facebook leads with search query: '{search_query}'")
            facebook_service = OpenAIApifyFacebookService()
            response = await facebook_service.fetch_posts_with_analysis(search_query, max_posts=25, analyze_sentiment=False)
            print(f"   Facebook API response success: {response.get('success')}")
            posts = response.get("posts", [])
            print(f"   Found {len(posts)} posts")

            leads = []
            for post in posts:
                created_date = datetime.utcnow()
                if post.get("created_at"):
                    try:
                        created_date = datetime.fromisoformat(
                            post["created_at"].replace("Z", "+00:00")
                        )
                    except:
                        pass

                post_text = post.get("text", "")
                lead = LeadCreate(
                    first_name=post.get("author", "Facebook User"),
                    last_name="",
                    username=post.get("author", ""),
                    mention=post_text,
                    lead_reason=post_text,
                    lead_status=LeadStatusEnum.NEW,
                    opportunity_type=LeadOpportunityTypeEnum.OTHER,
                    tags=[],
                    lead_link=post.get("url", ""),
                    social_profile_link=post.get("url", ""),
                    facebook_url=post.get("url", ""),
                    picture_url="",
                    created_date=created_date,
                    last_updated=created_date,
                    lead_type=LeadFormTypeEnum.CONVERSATIONAL,
                    website_url=post.get("url", ""),
                    lead_source=LeadSourceEnum.FACEBOOK,
                    assigned_to=user_id,
                    starred=False,
                    lead_form_snapshot_id=lead_form_id,
                    content_hash=ContentDeduplicator.generate_content_hash(post_text),
                )

                # Add sentiment and confidence if available
                if "sentiment" in post:
                    lead.notes = f"Sentiment: {post['sentiment']}"
                if "confidence" in post:
                    lead.score = int(float(post.get("confidence", 0)) * 100)

                leads.append(lead)

            return leads
        except Exception as e:
            print(f"❌ Error fetching Facebook leads: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    async def _fetch_tiktok_leads(
        search_query: str,
        user_id: str,
        lead_form_id: Optional[str] = None
    ) -> List[LeadCreate]:
        """Fetch leads from TikTok using Apify with smart search query"""
        try:
            print(f"🎵 Fetching TikTok leads with search query: '{search_query}'")
            tiktok_service = OpenAIApifyTiktokService()
            response = await tiktok_service.fetch_posts_with_analysis(search_query, max_posts=25, analyze_sentiment=False)
            print(f"   TikTok API response success: {response.get('success')}")
            posts = response.get("posts", [])
            print(f"   Found {len(posts)} posts")

            leads = []
            for post in posts:
                created_date = datetime.utcnow()

                # Handle TikTok timestamp formats
                if "createTime" in post and isinstance(post["createTime"], (int, float)):
                    created_date = datetime.fromtimestamp(post["createTime"])
                elif "created_at" in post:
                    try:
                        created_date = datetime.fromisoformat(
                            post["created_at"].replace("Z", "+00:00")
                        )
                    except:
                        pass

                post_text = post.get("text") or post.get("desc", "")
                lead = LeadCreate(
                    first_name=post.get("author") or post.get("username", "TikTok User"),
                    last_name="",
                    username=post.get("author") or post.get("username", ""),
                    mention=post_text,
                    lead_reason=post_text,
                    lead_status=LeadStatusEnum.NEW,
                    opportunity_type=LeadOpportunityTypeEnum.OTHER,
                    tags=[],
                    lead_link=post.get("url") or post.get("webVideoUrl") or post.get("video_url", ""),
                    social_profile_link=post.get("url") or post.get("webVideoUrl") or post.get("video_url", ""),
                    picture_url="",
                    created_date=created_date,
                    last_updated=created_date,
                    lead_type=LeadFormTypeEnum.CONVERSATIONAL,
                    website_url=post.get("url") or post.get("webVideoUrl") or post.get("video_url", ""),
                    lead_source=LeadSourceEnum.TIKTOK,
                    assigned_to=user_id,
                    starred=False,
                    lead_form_snapshot_id=lead_form_id,
                    content_hash=ContentDeduplicator.generate_content_hash(post_text),
                )

                # Add sentiment and confidence if available
                if "sentiment" in post:
                    lead.notes = f"Sentiment: {post['sentiment']}"
                if "confidence" in post:
                    lead.score = int(float(post.get("confidence", 0)) * 100)

                leads.append(lead)

            return leads
        except Exception as e:
            print(f"❌ Error fetching TikTok leads: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    async def _save_leads_batch(
        db: AsyncIOMotorDatabase,
        leads: List[LeadCreate]
    ) -> Dict:
        """Save multiple leads to database, returns statistics"""
        try:
            result = await LeadRepository.multiple_create_leads(db, leads)
            return result.get("responseData", {})
        except Exception as e:
            print(f"Error saving leads batch: {str(e)}")
            raise

    @staticmethod
    def _build_category_config(lead_form: Dict) -> CategoryConfig:
        """
        Build CategoryConfig from lead form data for intent analysis
        """
        # Extract configuration from lead form
        category_context = lead_form.get("category_context", "General product/service")
        keywords = lead_form.get("keywords", [])
        implied_keywords = lead_form.get("implied_keywords", [])
        competitors = lead_form.get("competitors", [])
        buying_signals = lead_form.get("buying_signals", [])
        excluded_keywords = lead_form.get("excluded_keywords", [])
        location = lead_form.get("location") or []  # Handle None case

        return CategoryConfig(
            category_context=category_context,
            keywords=keywords,
            implied_keywords=implied_keywords,
            competitors=competitors,
            buying_signals=buying_signals,
            excluded_keywords=excluded_keywords,
            location=location
        )

    @staticmethod
    async def _analyze_single_lead(
        lead: LeadCreate,
        category_config: CategoryConfig,
        intent_min: float,
        relevance_min: float,
        final_min: float
    ) -> tuple[LeadCreate | None, str]:
        """
        Analyze a single lead for buying intent

        Returns:
            Tuple of (lead if qualified else None, status message)
        """
        try:
            # Get post text from mention field
            post_text = lead.mention or lead.lead_reason or ""
            if not post_text.strip():
                return None, f"Skipping {lead.username}: no text content"

            # Run intent analysis
            intent_result = await IntentAnalysisService.analyze_post(
                text=post_text,
                config=category_config,
                model="gpt-4o-mini"
            )

            # Calculate final score
            final_score = IntentAnalysisService.calculate_final_score(
                intent_result.intent_score,
                intent_result.relevance_score,
                intent_result.urgency_flag
            )

            # Map intent category enum
            intent_category_map = {
                "direct": IntentCategoryEnum.DIRECT,
                "implied": IntentCategoryEnum.IMPLIED,
                "problem": IntentCategoryEnum.PROBLEM,
                "comparison": IntentCategoryEnum.COMPARISON,
                "competitor_negative": IntentCategoryEnum.COMPETITOR_NEGATIVE,
                "unknown": IntentCategoryEnum.UNKNOWN
            }

            # Map sentiment enum
            sentiment_map = {
                "positive": SentimentTypeEnum.POSITIVE,
                "negative": SentimentTypeEnum.NEGATIVE,
                "neutral": SentimentTypeEnum.NEUTRAL
            }

            # Populate intent fields in lead
            lead.intent_score = intent_result.intent_score
            lead.relevance_score = intent_result.relevance_score
            lead.urgency_flag = intent_result.urgency_flag
            lead.sentiment = sentiment_map.get(intent_result.sentiment.value, SentimentTypeEnum.NEUTRAL)
            lead.intent_category = intent_category_map.get(intent_result.intent_category.value, IntentCategoryEnum.UNKNOWN)
            lead.final_score = final_score
            lead.intent_reasoning = intent_result.reasoning

            # Check if meets qualification thresholds
            is_qualified = (
                intent_result.intent_score >= intent_min and
                intent_result.relevance_score >= relevance_min and
                final_score >= final_min
            )

            if is_qualified:
                status = f"✅ QUALIFIED: {lead.username} | Intent:{intent_result.intent_score:.2f} Relevance:{intent_result.relevance_score:.2f} Final:{final_score:.2f}\n   POST: {post_text[:200]}\n   REASONING: {intent_result.reasoning}"
                return lead, status
            else:
                status = f"❌ FILTERED: {lead.username} | Intent:{intent_result.intent_score:.2f} Relevance:{intent_result.relevance_score:.2f} Final:{final_score:.2f}\n   POST: {post_text[:200]}\n   REASONING: {intent_result.reasoning}"
                return None, status

        except Exception as e:
            error_msg = f"Error analyzing lead {lead.username}: {str(e)}"
            return None, error_msg

    @staticmethod
    async def _analyze_and_filter_leads(
        leads: List[LeadCreate],
        category_config: CategoryConfig,
        intent_min: float = 0.50,
        relevance_min: float = 0.45,
        final_min: float = 0.55
    ) -> List[LeadCreate]:
        """
        Analyze all leads for buying intent in parallel with adaptive thresholds

        First attempts with default thresholds. If zero results, automatically
        relaxes thresholds and retries to catch borderline leads.

        Args:
            leads: List of LeadCreate objects
            category_config: Category configuration for intent analysis
            intent_min, relevance_min, final_min: Qualification thresholds

        Returns:
            List of qualified LeadCreate objects with intent scores populated
        """
        if not leads:
            return []

        print(f"📊 INTENT ANALYSIS: Analyzing {len(leads)} posts in parallel for lead qualification...")

        # Process all leads in parallel using asyncio.gather
        tasks = [
            ConversationalLeadJobService._analyze_single_lead(
                lead, category_config, intent_min, relevance_min, final_min
            )
            for lead in leads
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect qualified leads and print results
        qualified_leads = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Exception during analysis: {str(result)}")
                continue

            lead, status = result
            print(status)
            if lead is not None:
                qualified_leads.append(lead)

        # ADAPTIVE THRESHOLDS: If zero results, try with relaxed thresholds
        if len(qualified_leads) == 0 and len(leads) > 0:
            print(f"⚠️ Zero leads qualified with default thresholds. Trying relaxed thresholds...")

            # Relaxed thresholds (lower by 0.10)
            relaxed_intent = intent_min - 0.10
            relaxed_relevance = relevance_min - 0.10
            relaxed_final = final_min - 0.10

            print(f"   Default: intent>={intent_min}, relevance>={relevance_min}, final>={final_min}")
            print(f"   Relaxed: intent>={relaxed_intent}, relevance>={relaxed_relevance}, final>={relaxed_final}")

            # Re-check all analyzed leads with relaxed thresholds
            relaxed_qualified = []
            for result in results:
                if isinstance(result, Exception):
                    continue

                # Get the lead from original results (already has scores populated)
                lead, _ = result
                if lead is None:
                    continue

                # Check if it meets relaxed thresholds
                if (lead.intent_score >= relaxed_intent and
                    lead.relevance_score >= relaxed_relevance and
                    lead.final_score >= relaxed_final):
                    relaxed_qualified.append(lead)

            if len(relaxed_qualified) > 0:
                print(f"✅ Found {len(relaxed_qualified)} leads with relaxed thresholds")
                print(f"💡 TIP: Consider using more specific keywords (e.g., 'need X' instead of 'affordable X') for better results")
                return relaxed_qualified
            else:
                print(f"❌ Still zero leads even with relaxed thresholds")
                print(f"💡 TIP: Your search keyword may be too generic or attracting wrong audience type")

        return qualified_leads

    @staticmethod
    def _convert_twitter_date(twitter_date: str) -> datetime:
        """Convert Twitter date format to datetime"""
        # Handle empty or None dates
        if not twitter_date or not twitter_date.strip():
            return datetime.utcnow()

        try:
            # Twitter format: "Sun Nov 09 17:51:05 +0000 2025"
            return datetime.strptime(twitter_date, "%a %b %d %H:%M:%S %z %Y")
        except Exception as e:
            print(f"Error converting Twitter date '{twitter_date}': {str(e)}")
            return datetime.utcnow()
