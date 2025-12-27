"""
SalesSignalJobService.py (formerly ConversationalLeadJobService.py)
Background job service for fetching Sales Signals from Twitter, Facebook, and TikTok.
Sales Signals are public online conversations that indicate buying intent, pain, or opportunity.
"""
import asyncio
import time
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.helpers.text_helper import TextHelper

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


class PlatformDistributionManager:
    """
    Manages platform distribution to enforce 70% Twitter, 20% Facebook, 10% TikTok
    with a maximum total of 150 posts across all keywords.
    """

    def __init__(self, max_total_posts: int = 150):
        """
        Initialize the distribution manager with dynamic smart limits.

        Args:
            max_total_posts: Maximum total posts to fetch (default: 150)
        """
        self.max_total_posts = max_total_posts
        self.twitter_target = int(max_total_posts * 0.70)  # 105 posts
        self.facebook_target = int(max_total_posts * 0.20)  # 30 posts
        self.tiktok_target = int(max_total_posts * 0.10)   # 15 posts

        # Running counters
        self.twitter_collected = 0
        self.facebook_collected = 0
        self.tiktok_collected = 0
        self.total_collected = 0

        print(f"🎯 Platform Distribution Manager Initialized:")
        print(f"   Target: {self.max_total_posts} total posts")
        print(f"   Twitter: {self.twitter_target} (70%)")
        print(f"   Facebook: {self.facebook_target} (20%)")
        print(f"   TikTok: {self.tiktok_target} (10%)")

    def get_keyword_limits(self, keyword_index: int, total_keywords: int, enabled_platforms: Dict) -> Dict[str, int]:
        """
        Smart dynamic limits that:
        1. Skip platforms that have reached their target
        2. Calculate remaining budget for each platform
        3. Distribute smartly across remaining keywords
        4. Never exceed platform targets

        Args:
            keyword_index: Current keyword index (1-based)
            total_keywords: Total number of keywords available
            enabled_platforms: Dict of enabled platforms

        Returns:
            Dict with max_posts per platform, skipping platforms at target
        """
        # Calculate remaining budget for each platform
        twitter_remaining = max(0, self.twitter_target - self.twitter_collected)
        facebook_remaining = max(0, self.facebook_target - self.facebook_collected)
        tiktok_remaining = max(0, self.tiktok_target - self.tiktok_collected)

        # Calculate remaining keywords (including current)
        remaining_keywords = total_keywords - keyword_index + 1

        # Smart distribution: divide remaining budget across remaining keywords
        # Use ceiling to ensure we fetch enough, but cap at remaining budget
        limits = {}

        # Twitter
        if BrowsercloudPlatformEnum.TWITTER.value.lower() in enabled_platforms:
            if twitter_remaining > 0:
                # Distribute remaining evenly, minimum 1 if any budget left
                twitter_limit = max(1, min(twitter_remaining, (twitter_remaining + remaining_keywords - 1) // remaining_keywords))
                limits["twitter"] = twitter_limit
            # else: skip Twitter (reached target)

        # Facebook
        if BrowsercloudPlatformEnum.FACEBOOK.value.lower() in enabled_platforms:
            if facebook_remaining > 0:
                facebook_limit = max(1, min(facebook_remaining, (facebook_remaining + remaining_keywords - 1) // remaining_keywords))
                limits["facebook"] = facebook_limit
            # else: skip Facebook (reached target)

        # TikTok
        if BrowsercloudPlatformEnum.TIKTOK.value.lower() in enabled_platforms:
            if tiktok_remaining > 0:
                tiktok_limit = max(1, min(tiktok_remaining, (tiktok_remaining + remaining_keywords - 1) // remaining_keywords))
                limits["tiktok"] = tiktok_limit
            # else: skip TikTok (reached target)

        print(f"   💡 Smart limits for keyword {keyword_index}/{total_keywords}:")
        print(f"      Remaining budget - Twitter: {twitter_remaining}, Facebook: {facebook_remaining}, TikTok: {tiktok_remaining}")
        print(f"      This keyword limits: {limits}")

        return limits

    def should_stop(self) -> bool:
        """
        Check if we've reached or exceeded the post limit.

        Returns:
            True if we should stop fetching more keywords
        """
        return self.total_collected >= self.max_total_posts

    def update_counts(self, twitter_count: int, facebook_count: int, tiktok_count: int):
        """
        Update running counters after fetching from platforms.

        Args:
            twitter_count: Number of posts fetched from Twitter
            facebook_count: Number of posts fetched from Facebook
            tiktok_count: Number of posts fetched from TikTok
        """
        self.twitter_collected += twitter_count
        self.facebook_collected += facebook_count
        self.tiktok_collected += tiktok_count
        self.total_collected = self.twitter_collected + self.facebook_collected + self.tiktok_collected

    def get_summary(self) -> str:
        """
        Get a summary of the current distribution.

        Returns:
            Formatted string with distribution stats
        """
        twitter_pct = (self.twitter_collected / self.total_collected * 100) if self.total_collected > 0 else 0
        facebook_pct = (self.facebook_collected / self.total_collected * 100) if self.total_collected > 0 else 0
        tiktok_pct = (self.tiktok_collected / self.total_collected * 100) if self.total_collected > 0 else 0

        return f"""
   📊 Platform Distribution Summary:
      Twitter:  {self.twitter_collected}/{self.twitter_target} ({twitter_pct:.1f}% - target 70%)
      Facebook: {self.facebook_collected}/{self.facebook_target} ({facebook_pct:.1f}% - target 20%)
      TikTok:   {self.tiktok_collected}/{self.tiktok_target} ({tiktok_pct:.1f}% - target 10%)
      Total:    {self.total_collected}/{self.max_total_posts} posts
"""


class LeadFilter:
    """
    Handles filtering of leads based on time range and location.
    """

    # Time range mappings
    TIME_RANGE_MAP = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "3m": timedelta(days=90),
        "6m": timedelta(days=180),
        "1y": timedelta(days=365),
        "all": None  # No time filter
    }

    @staticmethod
    def calculate_cutoff_date(post_age_filter: str) -> Optional[datetime]:
        """
        Calculate the cutoff date based on the post age filter.

        Args:
            post_age_filter: Time range string ("24h", "7d", "30d", "3m", "6m", "1y", "all")

        Returns:
            Cutoff datetime or None if "all"
        """
        if not post_age_filter or post_age_filter == "all":
            return None

        time_delta = LeadFilter.TIME_RANGE_MAP.get(post_age_filter)
        if not time_delta:
            print(f"⚠️ Invalid post_age_filter '{post_age_filter}', defaulting to 'all'")
            return None

        cutoff_date = datetime.now(timezone.utc) - time_delta
        return cutoff_date

    @staticmethod
    def filter_by_time_range(leads: List, cutoff_date: Optional[datetime]) -> List:
        """
        Filter leads by creation date.

        Args:
            leads: List of LeadCreate objects
            cutoff_date: Minimum date for leads (or None for no filter)

        Returns:
            Filtered list of leads
        """
        if not cutoff_date:
            return leads  # No time filter

        filtered_leads = []
        filtered_out_count = 0
        unknown_date_count = 0
        oldest_date = None
        newest_date = None

        for lead in leads:
            if hasattr(lead, 'created_date') and lead.created_date:
                # Ensure created_date is datetime object
                lead_date = lead.created_date if isinstance(lead.created_date, datetime) else datetime.fromisoformat(str(lead.created_date).replace('Z', '+00:00'))
                if lead_date.tzinfo is None:
                    lead_date = lead_date.replace(tzinfo=timezone.utc)

                # Check if this is a default/invalid timestamp (1970)
                if lead_date.year == 1970:
                    # Unknown date - INCLUDE the lead (don't filter it out)
                    filtered_leads.append(lead)
                    unknown_date_count += 1
                    continue

                # Track date range for valid dates only
                if oldest_date is None or lead_date < oldest_date:
                    oldest_date = lead_date
                if newest_date is None or lead_date > newest_date:
                    newest_date = lead_date

                if lead_date >= cutoff_date:
                    filtered_leads.append(lead)
                else:
                    filtered_out_count += 1
            else:
                # No created_date - INCLUDE the lead (don't filter it out)
                filtered_leads.append(lead)
                unknown_date_count += 1

        # Log filtering results
        if unknown_date_count > 0:
            print(f"   ⚠️ {unknown_date_count} posts have unknown dates - including them (scraper didn't provide timestamps)")
        if filtered_out_count > 0 and oldest_date and newest_date:
            print(f"   📅 Valid posts date range: {oldest_date.strftime('%Y-%m-%d')} to {newest_date.strftime('%Y-%m-%d')}")
            print(f"   🔍 Cutoff date: {cutoff_date.strftime('%Y-%m-%d')} (keeping posts >= this date)")

        return filtered_leads

    @staticmethod
    def filter_by_location(leads: List, target_locations: Optional[List[str]]) -> List:
        """
        Filter leads by location - strict matching.

        Args:
            leads: List of LeadCreate objects
            target_locations: List of location strings to match (e.g., ["Lagos", "Nigeria"])

        Returns:
            Filtered list of leads that match any of the target locations
        """
        if not target_locations or len(target_locations) == 0:
            return leads  # No location filter

        filtered_leads = []

        # Normalize target locations for comparison
        normalized_targets = [loc.lower().strip() for loc in target_locations]

        for lead in leads:
            # Check multiple potential location fields
            lead_location_text = ""

            # Extract location from various fields
            if hasattr(lead, 'location') and lead.location:
                lead_location_text += f" {lead.location}"
            if hasattr(lead, 'mention') and lead.mention:
                lead_location_text += f" {lead.mention}"
            if hasattr(lead, 'lead_reason') and lead.lead_reason:
                lead_location_text += f" {lead.lead_reason}"

            lead_location_lower = lead_location_text.lower()

            # Check if any target location is mentioned in the lead content
            if any(target in lead_location_lower for target in normalized_targets):
                filtered_leads.append(lead)

        return filtered_leads


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
    Service to handle background jobs for fetching sales signals
    from multiple social media platforms.
    """

    # ThreadPoolExecutor for CPU-bound LLM API calls
    # This prevents blocking the async event loop during intensive operations
    _llm_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="llm_worker")

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

            # PRD Section 5: Separate job keywords for Job Boards platform
            job_keywords = lead_form.get("job_keywords", [])

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

            # Build prioritized keyword list (ALL AVAILABLE KEYWORDS)
            # Strategy: Start with best keywords, continue until 150 posts reached
            # 1. Add first 4 direct keywords (2 with 3+ words, 2 with 2 words)
            if keywords and len(keywords) > 0:
                direct_selected = select_keywords_by_word_count(keywords, target_count=4)
                prioritized_keywords.extend(direct_selected)
                print(f"   📝 Direct keywords selected (first 4): {direct_selected}")

            # 2. Add first 4 implied keywords (2 with 3+ words, 2 with 2 words)
            if implied_keywords and len(implied_keywords) > 0:
                implied_selected = select_keywords_by_word_count(implied_keywords, target_count=4)
                prioritized_keywords.extend(implied_selected)
                print(f"   📝 Implied keywords selected (first 4): {implied_selected}")

            # 3. Add remaining direct keywords (5th, 6th, 7th... if available)
            if keywords and len(keywords) > 4:
                remaining_direct = select_keywords_by_word_count(keywords[4:], target_count=len(keywords) - 4)
                prioritized_keywords.extend(remaining_direct)
                print(f"   📝 Additional direct keywords: {remaining_direct}")

            # 4. Add remaining implied keywords (5th, 6th, 7th... if available)
            if implied_keywords and len(implied_keywords) > 4:
                remaining_implied = select_keywords_by_word_count(implied_keywords[4:], target_count=len(implied_keywords) - 4)
                prioritized_keywords.extend(remaining_implied)
                print(f"   📝 Additional implied keywords: {remaining_implied}")

            # 5. Fallback: If still low on keywords, use buying signals
            if len(prioritized_keywords) < 8 and buying_signals and len(buying_signals) > 0:
                remaining_slots = max(4, 12 - len(prioritized_keywords))  # Get at least 4 buying signals
                signal_selected = select_keywords_by_word_count(buying_signals, target_count=remaining_slots)
                prioritized_keywords.extend(signal_selected)
                print(f"   📝 Buying signal keywords selected: {signal_selected}")

            if not prioritized_keywords:
                print(f"⚠️ No keywords available for search")
                return stats

            print(f"🎯 Prioritized keywords ({len(prioritized_keywords)} total): {prioritized_keywords}")

            # Build category configuration once (used for intent analysis)
            category_config = ConversationalLeadJobService._build_category_config(lead_form)

            # Get custom scoring thresholds if specified
            scoring_thresholds = lead_form.get("scoring_thresholds", {})
            intent_min = scoring_thresholds.get("intent_score_min", 0.50)
            relevance_min = scoring_thresholds.get("relevance_score_min", 0.45)
            final_min = scoring_thresholds.get("final_score_min", 0.55)

            # Update progress: Starting keyword search
            await update_progress(10, f"Searching with {len(prioritized_keywords)} keyword(s) across {len(enabled_platforms)} platform(s)...")

            # Initialize platform distribution manager (70% Twitter, 20% Facebook, 10% TikTok, max 150 posts)
            distribution_manager = PlatformDistributionManager(max_total_posts=150)

            # Try ALL keywords to maximize qualified leads (with early stopping at 150 posts)
            qualified_leads = []
            for keyword_idx, keyword in enumerate(prioritized_keywords, 1):
                # Check if we should stop early (reached 150 post limit)
                if distribution_manager.should_stop():
                    print(f"\n✅ Reached {distribution_manager.max_total_posts} post limit, stopping early at keyword {keyword_idx}/{len(prioritized_keywords)}")
                    print(distribution_manager.get_summary())
                    break

                print(f"\n🔍 KEYWORD ATTEMPT {keyword_idx}/{len(prioritized_keywords)}: '{keyword}'")
                progress_percent = 10 + (keyword_idx * 20)  # 10, 30, 50
                await update_progress(progress_percent, f"Fetching from platforms with keyword '{keyword}'...")

                # Get smart dynamic limits for this keyword based on remaining budget and remaining keywords
                keyword_limits = distribution_manager.get_keyword_limits(keyword_idx, len(prioritized_keywords), enabled_platforms)

                # CONCURRENT FETCHING: Optimize keywords per platform and fetch in parallel
                fetch_tasks = []
                platform_timeout = 45  # 45 seconds per platform

                # Twitter - only fetch if limit exists (not at target)
                if BrowsercloudPlatformEnum.TWITTER.value.lower() in enabled_platforms and "twitter" in keyword_limits:
                    twitter_keyword = PlatformKeywordOptimizer.optimize_for_twitter(keyword)
                    twitter_limit = keyword_limits["twitter"]
                    print(f"   🐦 Twitter: '{twitter_keyword}' (max: {twitter_limit} posts)")
                    fetch_tasks.append(
                        asyncio.wait_for(
                            ConversationalLeadJobService._fetch_twitter_leads(
                                twitter_keyword, user_id, lead_form.get("lead_form_id"), max_posts=twitter_limit
                            ),
                            timeout=platform_timeout
                        )
                    )
                elif BrowsercloudPlatformEnum.TWITTER.value.lower() in enabled_platforms:
                    print(f"   🐦 Twitter: SKIPPED (target reached)")

                # Facebook - only fetch if limit exists (not at target)
                if BrowsercloudPlatformEnum.FACEBOOK.value.lower() in enabled_platforms and "facebook" in keyword_limits:
                    facebook_keyword = PlatformKeywordOptimizer.optimize_for_facebook(keyword)
                    facebook_limit = keyword_limits["facebook"]
                    print(f"   📘 Facebook: '{facebook_keyword}' (max: {facebook_limit} posts)")
                    fetch_tasks.append(
                        asyncio.wait_for(
                            ConversationalLeadJobService._fetch_facebook_leads(
                                facebook_keyword, user_id, lead_form.get("lead_form_id"), max_posts=facebook_limit
                            ),
                            timeout=platform_timeout
                        )
                    )
                elif BrowsercloudPlatformEnum.FACEBOOK.value.lower() in enabled_platforms:
                    print(f"   📘 Facebook: SKIPPED (target reached)")

                # TikTok - only fetch if limit exists (not at target)
                if BrowsercloudPlatformEnum.TIKTOK.value.lower() in enabled_platforms and "tiktok" in keyword_limits:
                    tiktok_keyword = PlatformKeywordOptimizer.optimize_for_tiktok(keyword)
                    tiktok_limit = keyword_limits["tiktok"]
                    print(f"   🎵 TikTok: '{tiktok_keyword}' (max: {tiktok_limit} posts)")
                    fetch_tasks.append(
                        asyncio.wait_for(
                            ConversationalLeadJobService._fetch_tiktok_leads(
                                tiktok_keyword, user_id, lead_form.get("lead_form_id"), max_posts=tiktok_limit
                            ),
                            timeout=platform_timeout
                        )
                    )
                elif BrowsercloudPlatformEnum.TIKTOK.value.lower() in enabled_platforms:
                    print(f"   🎵 TikTok: SKIPPED (target reached)")

                # PRD Section 5: Job Boards use job_keywords array (not regular keywords)
                if BrowsercloudPlatformEnum.JOB_BOARDS.value.lower() in enabled_platforms:
                    solution_context = lead_form.get("solution_context", "")

                    # PRD: Fetch from user onboarding if solution_context not provided
                    if not solution_context or solution_context.strip() == "":
                        print(f"   📥 No solution_context, fetching from user onboarding...")
                        from app.services.uri_microservices.UriBackendService import UriBackendService
                        user_details = await UriBackendService.get_user_details(user_id)

                        if user_details and user_details.get("businessDetails"):
                            what_you_sell = user_details["businessDetails"].get("whatYouSell")
                            if what_you_sell and what_you_sell.strip():
                                solution_context = what_you_sell
                                print(f"   ✅ Using user onboarding whatYouSell: {solution_context[:50]}...")

                    # Use job_keywords if available, otherwise fallback to current keyword
                    job_keyword_to_use = keyword  # Default fallback
                    if job_keywords and len(job_keywords) > 0:
                        # Use the corresponding job keyword if available (by index)
                        keyword_index = keyword_idx - 1
                        if keyword_index < len(job_keywords):
                            job_keyword_to_use = job_keywords[keyword_index]
                        else:
                            # If we've exhausted job_keywords, use first one as fallback
                            job_keyword_to_use = job_keywords[0]

                    print(f"   💼 Job Boards: '{job_keyword_to_use}' (max: 20 jobs)")
                    if solution_context and solution_context.strip():
                        fetch_tasks.append(
                            asyncio.wait_for(
                                ConversationalLeadJobService._fetch_job_board_signals(
                                    job_keyword_to_use, user_id, lead_form.get("lead_form_id"), solution_context, max_jobs=20
                                ),
                                timeout=90  # Longer timeout for job scraping + AI analysis
                            )
                        )
                    else:
                        print(f"   ⚠️ Job Boards enabled but no solution_context available (not in form or user onboarding) - skipping")

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

                # Update distribution manager counters
                twitter_count = len([l for l in keyword_leads if l.lead_source == LeadSourceEnum.X])
                facebook_count = len([l for l in keyword_leads if l.lead_source == LeadSourceEnum.FACEBOOK])
                tiktok_count = len([l for l in keyword_leads if l.lead_source == LeadSourceEnum.TIKTOK])

                distribution_manager.update_counts(twitter_count, facebook_count, tiktok_count)

                print(f"   📊 Platform distribution progress:")
                print(f"      Twitter:  {distribution_manager.twitter_collected}/{distribution_manager.twitter_target}")
                print(f"      Facebook: {distribution_manager.facebook_collected}/{distribution_manager.facebook_target}")
                print(f"      TikTok:   {distribution_manager.tiktok_collected}/{distribution_manager.tiktok_target}")
                print(f"      Total:    {distribution_manager.total_collected}/{distribution_manager.max_total_posts}")

                # Apply time range and location filters
                if keyword_leads:
                    # Extract filter parameters from lead_form
                    post_age_filter = lead_form.get("post_age_filter", "all")
                    location_filter = lead_form.get("location") or []

                    # Calculate cutoff date for time filtering
                    cutoff_date = LeadFilter.calculate_cutoff_date(post_age_filter)

                    # Apply time range filter
                    leads_after_time_filter = LeadFilter.filter_by_time_range(keyword_leads, cutoff_date)
                    time_filtered_count = len(keyword_leads) - len(leads_after_time_filter)
                    if time_filtered_count > 0:
                        print(f"   🕒 Filtered out {time_filtered_count} leads older than {post_age_filter}")

                    # Apply location filter
                    leads_after_location_filter = LeadFilter.filter_by_location(leads_after_time_filter, location_filter)
                    location_filtered_count = len(leads_after_time_filter) - len(leads_after_location_filter)
                    if location_filtered_count > 0:
                        print(f"   📍 Filtered out {location_filtered_count} leads not matching location {location_filter}")

                    print(f"   ✅ {len(leads_after_location_filter)} leads passed filters (from {len(keyword_leads)} raw)")

                    # Analyze filtered leads
                    if leads_after_location_filter:
                        keyword_qualified = await ConversationalLeadJobService._analyze_and_filter_leads(
                            leads_after_location_filter, category_config, intent_min, relevance_min, final_min
                        )
                        qualified_leads.extend(keyword_qualified)
                        print(f"   ✅ {len(keyword_qualified)} qualified from this keyword")
                        print(f"   📈 TOTAL QUALIFIED SO FAR: {len(qualified_leads)}")
                    else:
                        print(f"   ⚠️ No leads passed filters for this keyword")

                # Continue with all keywords to maximize results (no early stopping)

            # Update statistics
            stats["total_fetched"] = len(all_leads)
            stats["total_qualified"] = len(qualified_leads)
            print(f"\n✅ INTENT ANALYSIS COMPLETE: {len(qualified_leads)}/{len(all_leads)} leads qualified")

            # Print final platform distribution summary
            print(distribution_manager.get_summary())

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
                        print(f"Failed to update feature limit after sales signals: {str(e)}")
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
        lead_form_id: Optional[str] = None,
        max_posts: int = 25
    ) -> List[LeadCreate]:
        """Fetch leads from Twitter using Apify with smart search query"""
        try:
            print(f"🐦 Fetching Twitter leads with search query: '{search_query}'")
            twitter_service = OpenAIApifyTwitterService()
            response = await twitter_service.fetch_tweets_with_analysis(search_query, max_tweets=max_posts, analyze_sentiment=False)
            print(f"   Twitter API response success: {response.get('success')}")
            tweets = response.get("tweets", [])
            print(f"   Found {len(tweets)} tweets")

            # DEBUG: Log first tweet structure to see available fields
            if tweets and len(tweets) > 0:
                print(f"   🔍 DEBUG - First tweet keys: {list(tweets[0].keys())}")
                print(f"   🔍 DEBUG - created_at value: '{tweets[0].get('created_at')}'")
                print(f"   🔍 DEBUG - Full first tweet: {tweets[0]}")

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
        lead_form_id: Optional[str] = None,
        max_posts: int = 25
    ) -> List[LeadCreate]:
        """Fetch leads from Facebook using Apify with smart search query"""
        try:
            print(f"📘 Fetching Facebook leads with search query: '{search_query}'")
            facebook_service = OpenAIApifyFacebookService()
            response = await facebook_service.fetch_posts_with_analysis(search_query, max_posts=max_posts, analyze_sentiment=False)
            print(f"   Facebook API response success: {response.get('success')}")
            posts = response.get("posts", [])
            print(f"   Found {len(posts)} posts")

            # DEBUG: Log first post structure to see available fields
            if posts and len(posts) > 0:
                print(f"   🔍 DEBUG - First post keys: {list(posts[0].keys())}")
                print(f"   🔍 DEBUG - created_at value: '{posts[0].get('created_at')}'")
                print(f"   🔍 DEBUG - Full first post: {posts[0]}")

            leads = []
            for post in posts:
                created_date = datetime(1970, 1, 1, tzinfo=timezone.utc)
                if post.get("created_at"):
                    try:
                        created_date = datetime.fromisoformat(
                            post["created_at"].replace("Z", "+00:00")
                        )
                    except:
                        pass
                if created_date.year == 1970:
                    extracted = (
                        TextHelper.extract_timestamp_from_text(post.get("text"))
                        or TextHelper.extract_timestamp_from_date_text(post.get("text"))
                        or TextHelper.extract_timestamp_from_relative_date_text(post.get("text"))
                    )
                    if extracted:
                        try:
                            created_date = datetime.fromisoformat(str(extracted).replace("Z", "+00:00"))
                        except Exception:
                            created_date = datetime(1970, 1, 1, tzinfo=timezone.utc)

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
        lead_form_id: Optional[str] = None,
        max_posts: int = 25
    ) -> List[LeadCreate]:
        """Fetch leads from TikTok using Apify with smart search query"""
        try:
            print(f"🎵 Fetching TikTok leads with search query: '{search_query}'")
            tiktok_service = OpenAIApifyTiktokService()
            response = await tiktok_service.fetch_posts_with_analysis(search_query, max_posts=max_posts, analyze_sentiment=False)
            print(f"   TikTok API response success: {response.get('success')}")
            posts = response.get("posts", [])
            print(f"   Found {len(posts)} posts")

            # DEBUG: Log first post structure to see available fields
            if posts and len(posts) > 0:
                print(f"   🔍 DEBUG - First video keys: {list(posts[0].keys())}")
                print(f"   🔍 DEBUG - createTime value: '{posts[0].get('createTime')}'")
                print(f"   🔍 DEBUG - created_at value: '{posts[0].get('created_at')}'")
                print(f"   🔍 DEBUG - Full first video: {posts[0]}")

            leads = []
            for post in posts:
                created_date = datetime(1970, 1, 1, tzinfo=timezone.utc)

                # Handle TikTok timestamp formats - created_at can be Unix timestamp (int) or ISO string
                created_at_value = post.get("created_at")

                if isinstance(created_at_value, (int, float)) and created_at_value > 0:
                    # Unix timestamp (e.g., 1728885285)
                    created_date = datetime.fromtimestamp(created_at_value, tz=timezone.utc)
                elif isinstance(created_at_value, str) and created_at_value.strip():
                    # Try ISO format string
                    try:
                        created_date = datetime.fromisoformat(created_at_value.replace("Z", "+00:00"))
                        if created_date.tzinfo is None:
                            created_date = created_date.replace(tzinfo=timezone.utc)
                    except:
                        pass
                elif "createTime" in post and isinstance(post["createTime"], (int, float)):
                    # Alternative field name
                    created_date = datetime.fromtimestamp(post["createTime"], tz=timezone.utc)
                if created_date.year == 1970:
                    post_text = post.get("text") or post.get("desc", "")
                    extracted = (
                        TextHelper.extract_timestamp_from_text(post_text)
                        or TextHelper.extract_timestamp_from_date_text(post_text)
                        or TextHelper.extract_timestamp_from_relative_date_text(post_text)
                    )
                    if extracted:
                        try:
                            created_date = datetime.fromisoformat(str(extracted).replace("Z", "+00:00"))
                        except Exception:
                            created_date = datetime(1970, 1, 1, tzinfo=timezone.utc)

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

        Handles backward compatibility with old forms that don't have
        category_context or implied_keywords fields.
        """
        # Extract configuration from lead form with fallbacks for None values
        # Use `or` to handle both missing keys and explicit None values
        category_context = lead_form.get("category_context") or "General product/service"
        keywords = lead_form.get("keywords") or []
        implied_keywords = lead_form.get("implied_keywords") or []
        competitors = lead_form.get("competitors") or []
        buying_signals = lead_form.get("buying_signals") or []
        excluded_keywords = lead_form.get("excluded_keywords") or []
        location = lead_form.get("location") or []

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

        # Process all leads in parallel using ThreadPoolExecutor + asyncio.gather
        # This offloads CPU-intensive LLM API calls to threads, preventing event loop blocking
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                ConversationalLeadJobService._llm_executor,
                lambda l=lead: asyncio.run(
                    ConversationalLeadJobService._analyze_single_lead(
                        l, category_config, intent_min, relevance_min, final_min
                    )
                )
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
    async def _fetch_job_board_signals(
        search_query: str,
        user_id: str,
        lead_form_id: Optional[str] = None,
        solution_context: str = "",
        max_jobs: int = 20
    ) -> List[LeadCreate]:
        """
        Fetch and analyze job postings from LinkedIn Jobs and Jobberman
        Pattern: Same as _fetch_twitter_leads() but for job boards

        Args:
            search_query: Search query for jobs (e.g., "DevOps Engineer")
            user_id: User ID to assign leads to
            lead_form_id: Lead form snapshot ID
            solution_context: User's solution description (for AI analysis)
            max_jobs: Maximum number of jobs to fetch

        Returns:
            List of LeadCreate objects from qualified job postings
        """
        try:
            print(f"💼 Fetching job board signals with query: '{search_query}'")

            # Import services
            from app.services.ApifyLinkedInJobsService import ApifyLinkedInJobsService
            from app.services.ApifyJobbermanService import ApifyJobbermanService
            from app.services.ApifyIndeedService import ApifyIndeedService
            from app.services.JobSignalAnalysisService import JobSignalAnalysisService

            # Initialize services
            linkedin_service = ApifyLinkedInJobsService()
            jobberman_service = ApifyJobbermanService()
            indeed_service = ApifyIndeedService()

            # PRD: Fetch from LinkedIn Jobs, Jobberman, and Indeed concurrently
            linkedin_result = await linkedin_service.fetch_job_postings(search_query, max_jobs=15)
            jobberman_result = await jobberman_service.fetch_job_postings(search_query, max_jobs=5)
            indeed_result = await indeed_service.fetch_job_postings(search_query, max_jobs=10)

            # Collect all jobs with source attribution
            all_jobs = []
            if linkedin_result.get("success"):
                for job in linkedin_result.get("jobs", []):
                    job["source"] = "LinkedIn Jobs"
                    all_jobs.append(job)
            if jobberman_result.get("success"):
                for job in jobberman_result.get("jobs", []):
                    job["source"] = "Jobberman"
                    all_jobs.append(job)
            if indeed_result.get("success"):
                for job in indeed_result.get("jobs", []):
                    job["source"] = "Indeed"
                    all_jobs.append(job)

            print(f"   Found {len(all_jobs)} total job postings (LinkedIn: {len(linkedin_result.get('jobs', []))}, Jobberman: {len(jobberman_result.get('jobs', []))}, Indeed: {len(indeed_result.get('jobs', []))})")

            if not all_jobs:
                print(f"   ⚠️ No jobs found for query '{search_query}'")
                return []

            # Deduplicate jobs (same company + similar title)
            deduplicated_jobs = ConversationalLeadJobService._deduplicate_jobs(all_jobs)
            print(f"   After deduplication: {len(deduplicated_jobs)} unique jobs")

            # Analyze each job posting with AI
            qualified_signals = []
            for job in deduplicated_jobs[:max_jobs]:  # Limit to max_jobs
                try:
                    # Run AI analysis
                    analysis = await JobSignalAnalysisService.analyze_job_posting(
                        job_description=job.get("description", ""),
                        job_title=job.get("title", ""),
                        company_name=job.get("company", ""),
                        solution_context=solution_context
                    )

                    # Filter by problem-solution match threshold (PRD requirement: >= 0.3)
                    if analysis.problem_solution_match >= 0.3:
                        # Create lead object (same pattern as Twitter/Facebook leads)
                        lead = LeadCreate(
                            first_name=job.get("company", "Unknown Company"),
                            last_name="",
                            username="",
                            mention=job.get("description", ""),
                            lead_reason=analysis.reasoning,  # AI explanation of why this is a sales signal
                            lead_status=LeadStatusEnum.NEW,
                            opportunity_type=LeadOpportunityTypeEnum.OTHER,
                            tags=[],
                            lead_link=job.get("url", ""),
                            website_url=job.get("url", ""),
                            created_date=datetime.now(timezone.utc),
                            last_updated=datetime.now(timezone.utc),
                            lead_type=LeadFormTypeEnum.CONVERSATIONAL,
                            lead_source=LeadSourceEnum.JOB_BOARDS,
                            assigned_to=user_id,
                            starred=False,
                            lead_form_snapshot_id=lead_form_id,
                            # Job-specific fields
                            job_posting_url=job.get("url", ""),
                            job_title_field=job.get("title", ""),
                            hiring_company=job.get("company", ""),
                            problem_solution_match=analysis.problem_solution_match,
                            hiring_intent_score=analysis.hiring_intent_score,
                            commercial_relevance=analysis.commercial_relevance,
                            implied_problems=analysis.implied_problems,
                            job_source=job.get("source", "Unknown"),
                            company_confidence=analysis.company_confidence,  # PRD Sections 14-16
                            # Intent analysis fields (for consistency with social media leads)
                            final_score=analysis.commercial_relevance,
                            intent_reasoning=analysis.reasoning,
                        )
                        qualified_signals.append(lead)
                        print(f"   ✅ QUALIFIED: {job.get('company')} - {job.get('title')} | Match:{analysis.problem_solution_match:.2f} Relevance:{analysis.commercial_relevance:.2f}")
                    else:
                        print(f"   ❌ FILTERED: {job.get('company')} - {job.get('title')} | Match:{analysis.problem_solution_match:.2f} (below 0.3 threshold)")

                except Exception as analysis_error:
                    print(f"   ⚠️ Error analyzing job {job.get('title')}: {str(analysis_error)}")
                    continue

            print(f"   ✅ {len(qualified_signals)} qualified job signals (from {len(deduplicated_jobs)} analyzed)")
            return qualified_signals

        except Exception as e:
            print(f"❌ Error fetching job board signals: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def _deduplicate_jobs(jobs: List[Dict]) -> List[Dict]:
        """
        Remove duplicate job postings across job boards
        PRD Section 13.1: De-duplication with semantic similarity

        Jobs are considered duplicates if ALL of the following match:
        - Company name (normalized)
        - Job title (semantic similarity ≥ 0.7)
        - Job description similarity (≥ 0.8 threshold)

        Source priority order (for display metadata):
        1. LinkedIn Jobs
        2. Jobberman
        3. Indeed

        Args:
            jobs: List of job dictionaries

        Returns:
            List of unique job dictionaries (retains highest priority source)
        """
        from difflib import SequenceMatcher

        # PRD Section 13.1: Source priority (LinkedIn Jobs > Jobberman > Indeed)
        source_priority = {
            "LinkedIn Jobs": 1,
            "Jobberman": 2,
            "Indeed": 3,
            "linkedin jobs": 1,
            "jobberman": 2,
            "indeed": 3
        }

        unique_jobs = []

        for job in jobs:
            is_duplicate = False
            company = job.get("company", "").lower().strip()
            title = job.get("title", "").lower().strip()
            description = job.get("description", "")[:500].lower().strip()  # First 500 chars

            # Check against existing unique jobs
            for i, existing in enumerate(unique_jobs):
                existing_company = existing.get("company", "").lower().strip()
                existing_title = existing.get("title", "").lower().strip()
                existing_description = existing.get("description", "")[:500].lower().strip()

                # 1. Company name match (normalized)
                if company != existing_company:
                    continue

                # 2. Job title similarity (semantic, not exact)
                title_similarity = SequenceMatcher(None, title, existing_title).ratio()
                if title_similarity < 0.7:  # 70% similarity threshold
                    continue

                # 3. Job description similarity
                if description and existing_description:
                    desc_similarity = SequenceMatcher(None, description, existing_description).ratio()
                    if desc_similarity < 0.8:  # 80% similarity threshold (PRD requirement)
                        continue

                # All conditions met - this is a duplicate
                is_duplicate = True

                # Apply source priority - keep higher priority source
                job_source = job.get("source", "")
                existing_source = existing.get("source", "")

                job_priority = source_priority.get(job_source, 999)
                existing_priority = source_priority.get(existing_source, 999)

                if job_priority < existing_priority:
                    # Replace with higher priority source
                    unique_jobs[i] = job
                    print(f"   🔁 Duplicate found, keeping higher priority: {company} - {title} (from {job_source})")
                else:
                    print(f"   🔁 Duplicate removed: {company} - {title} (lower priority: {job_source})")

                break

            if not is_duplicate:
                unique_jobs.append(job)

        return unique_jobs

    @staticmethod
    def _convert_twitter_date(twitter_date: str) -> datetime:
        """Convert Twitter date format to datetime"""
        # Handle empty or None dates
        if not twitter_date or not twitter_date.strip():
            return datetime(1970, 1, 1, tzinfo=timezone.utc)

        try:
            iso_candidate = twitter_date.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_candidate)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
        try:
            return datetime.strptime(twitter_date, "%a %b %d %H:%M:%S %z %Y")
        except Exception as e:
            print(f"Error converting Twitter date '{twitter_date}': {str(e)}")
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
