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
from typing import Dict, List, Optional, Any
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

# === SPAM FEATURE IMPORTS (NEW - for spam visibility feature) ===
from app.repository.SpamLeadRepository import SpamLeadRepository
from app.domain.schemas.spam_lead_schema import SpamLeadCreate
from app.domain.enums.spam_enum import SpamReasonEnum, SpamFilterStageEnum


class PlatformDistributionManager:
    """
    Manages platform distribution to enforce limits:
    - Social: 150 posts max (70% Twitter, 20% Facebook, 10% TikTok)
    - Job Boards: 50 posts max
    - Total: 200 posts across all sources
    """

    def __init__(self, max_social_posts: int = 150, max_job_posts: int = 50):
        """
        Initialize the distribution manager with dynamic smart limits.

        Args:
            max_social_posts: Maximum social media posts to fetch (default: 150)
            max_job_posts: Maximum job board posts to fetch (default: 50)
        """
        self.max_social_posts = max_social_posts
        self.max_job_posts = max_job_posts
        self.max_total_posts = max_social_posts + max_job_posts  # 200 total

        self.twitter_target = int(max_social_posts * 0.70)  # 105 posts
        self.facebook_target = int(max_social_posts * 0.20)  # 30 posts
        self.tiktok_target = int(max_social_posts * 0.10)   # 15 posts

        # Running counters
        self.twitter_collected = 0
        self.facebook_collected = 0
        self.tiktok_collected = 0
        self.job_boards_collected = 0
        self.total_social_collected = 0
        self.total_collected = 0

        print(f"🎯 Platform Distribution Manager Initialized:")
        print(f"   Total Target: {self.max_total_posts} posts")
        print(f"   Social Media: {self.max_social_posts} posts max")
        print(f"      Twitter: {self.twitter_target} (70%)")
        print(f"      Facebook: {self.facebook_target} (20%)")
        print(f"      TikTok: {self.tiktok_target} (10%)")
        print(f"   Job Boards: {self.max_job_posts} posts max")

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

        # Job Boards
        job_boards_remaining = max(0, self.max_job_posts - self.job_boards_collected)
        if BrowsercloudPlatformEnum.JOB_BOARDS.value.lower() in enabled_platforms:
            if job_boards_remaining > 0:
                # Distribute remaining job board budget across remaining keywords
                job_boards_limit = max(1, min(job_boards_remaining, (job_boards_remaining + remaining_keywords - 1) // remaining_keywords))
                limits["job_boards"] = job_boards_limit
            # else: skip Job Boards (reached target)

        print(f"   💡 Smart limits for keyword {keyword_index}/{total_keywords}:")
        print(f"      Remaining budget - Twitter: {twitter_remaining}, Facebook: {facebook_remaining}, TikTok: {tiktok_remaining}, Job Boards: {job_boards_remaining}")
        print(f"      This keyword limits: {limits}")

        return limits

    def should_stop(self) -> bool:
        """
        Check if we've reached or exceeded the post limit.

        Returns:
            True if we should stop fetching more keywords
        """
        # Stop if we've reached the grand total of 250 posts
        return self.total_collected >= self.max_total_posts

    def update_counts(self, twitter_count: int, facebook_count: int, tiktok_count: int, job_boards_count: int = 0):
        """
        Update running counters after fetching from platforms.

        Args:
            twitter_count: Number of posts fetched from Twitter
            facebook_count: Number of posts fetched from Facebook
            tiktok_count: Number of posts fetched from TikTok
            job_boards_count: Number of posts fetched from Job Boards
        """
        self.twitter_collected += twitter_count
        self.facebook_collected += facebook_count
        self.tiktok_collected += tiktok_count
        self.job_boards_collected += job_boards_count
        self.total_social_collected = self.twitter_collected + self.facebook_collected + self.tiktok_collected
        self.total_collected = self.total_social_collected + self.job_boards_collected

    def get_summary(self) -> str:
        """
        Get a summary of the current distribution.

        Returns:
            Formatted string with distribution stats
        """
        twitter_pct = (self.twitter_collected / self.total_social_collected * 100) if self.total_social_collected > 0 else 0
        facebook_pct = (self.facebook_collected / self.total_social_collected * 100) if self.total_social_collected > 0 else 0
        tiktok_pct = (self.tiktok_collected / self.total_social_collected * 100) if self.total_social_collected > 0 else 0

        return f"""
   📊 Platform Distribution Summary:
      Social Media: {self.total_social_collected}/{self.max_social_posts}
         Twitter:  {self.twitter_collected}/{self.twitter_target} ({twitter_pct:.1f}% - target 70%)
         Facebook: {self.facebook_collected}/{self.facebook_target} ({facebook_pct:.1f}% - target 20%)
         TikTok:   {self.tiktok_collected}/{self.tiktok_target} ({tiktok_pct:.1f}% - target 10%)
      Job Boards: {self.job_boards_collected}/{self.max_job_posts}
      Grand Total: {self.total_collected}/{self.max_total_posts} posts
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
    async def _check_cancellation(db: AsyncIOMotorDatabase, job_id: str) -> bool:
        """
        Check if cancellation was requested for this job.

        This is called during the keyword loop to detect cancellation requests.
        Returns True if job should stop.

        Performance: Single DB query per check
        """
        if not job_id:
            return False

        from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository

        try:
            job = await LeadGenerationJobRepository.get_job_status(db, job_id)

            if job and job.get("status") == "cancelling":
                print(f"🛑 Cancellation detected for job {job_id}")
                return True

            return False

        except Exception as e:
            print(f"⚠️ Error checking cancellation: {str(e)}")
            # On error, don't stop - let job continue
            return False

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
            # Social platform stats
            "social_total_fetched": 0,
            "social_qualified": 0,
            "social_new_leads": 0,
            "social_duplicates": 0,

            # Job board stats
            "job_boards_total_fetched": 0,  # Total jobs fetched (before AI filtering)
            "job_signals_found": 0,  # Qualified job signals (after AI filtering)
            "job_signals_saved": 0,
            "job_signals_high_match": 0,
            "job_signals_medium_match": 0,
            "job_signals_low_match": 0,

            # Combined totals (for backward compatibility)
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

            # Check if ONLY job boards are enabled (no social platforms)
            has_social_platforms = any(p in enabled_platforms for p in [
                BrowsercloudPlatformEnum.TWITTER.value.lower(),
                BrowsercloudPlatformEnum.FACEBOOK.value.lower(),
                BrowsercloudPlatformEnum.TIKTOK.value.lower()
            ])
            has_job_boards = BrowsercloudPlatformEnum.JOB_BOARDS.value.lower() in enabled_platforms
            only_job_boards = has_job_boards and not has_social_platforms

            # Build prioritized keyword list
            # SCENARIO 3: If ONLY job boards enabled, use job_keywords directly
            if only_job_boards:
                if job_keywords and len(job_keywords) > 0:
                    prioritized_keywords = list(job_keywords)
                    print(f"🎯 Job boards ONLY mode: Using {len(prioritized_keywords)} job keywords: {prioritized_keywords}")
                else:
                    print(f"⚠️ Job boards enabled but no job_keywords available")
                    return stats
            else:
                # SCENARIO 1 & 2: Social platforms enabled (alone or with job boards)
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

            # For job boards: Prepare keywords and counter
            import random
            job_board_keywords = []
            job_keyword_index = 0  # Track which job keyword to use next (for SCENARIO 2)

            if has_job_boards:
                if only_job_boards:
                    # SCENARIO 3: Only job boards - use all prioritized_keywords (which are job_keywords)
                    job_board_keywords = random.sample(prioritized_keywords, min(4, len(prioritized_keywords)))
                    print(f"💼 Job boards ONLY: Starting with {len(job_board_keywords)} keywords: {job_board_keywords}")
                else:
                    # SCENARIO 2: Both social + job boards - use job_keywords independently
                    if job_keywords and len(job_keywords) > 0:
                        job_board_keywords = random.sample(job_keywords, min(4, len(job_keywords)))
                        print(f"💼 Job boards (parallel with social): Will use {len(job_board_keywords)} job keywords: {job_board_keywords}")
                    else:
                        print(f"⚠️ Job boards enabled but no job_keywords available - job boards will be skipped")

            # Build category configuration once (used for intent analysis)
            category_config = ConversationalLeadJobService._build_category_config(lead_form)

            # Get custom scoring thresholds if specified
            scoring_thresholds = lead_form.get("scoring_thresholds", {})
            intent_min = scoring_thresholds.get("intent_score_min", 0.50)
            relevance_min = scoring_thresholds.get("relevance_score_min", 0.45)
            final_min = scoring_thresholds.get("final_score_min", 0.55)

            # Update progress: Starting keyword search
            await update_progress(10, f"Searching with {len(prioritized_keywords)} keyword(s) across {len(enabled_platforms)} platform(s)...")

            # Initialize platform distribution manager (150 social + 50 job boards = 200 total)
            distribution_manager = PlatformDistributionManager(max_social_posts=150, max_job_posts=50)

            # Track total job posts fetched across all keywords (before AI filtering)
            job_boards_total_fetched = 0

            # Try ALL keywords to maximize qualified leads (with early stopping at 150 posts)
            qualified_leads = []
            cancelled_early = False  # Track if job was cancelled
            for keyword_idx, keyword in enumerate(prioritized_keywords, 1):
                # Check for cancellation request
                if await ConversationalLeadJobService._check_cancellation(db, job_id):
                    print(f"🛑 Job cancelled by user at keyword {keyword_idx}/{len(prioritized_keywords)}")
                    print(f"   Processed {keyword_idx - 1} keywords before cancellation")
                    print(f"   Current stats: {distribution_manager.total_collected} posts fetched")
                    cancelled_early = True
                    break

                # Check if we should stop early (reached 150 post limit)
                if distribution_manager.should_stop():
                    print(f"\n✅ Reached {distribution_manager.max_total_posts} post limit, stopping early at keyword {keyword_idx}/{len(prioritized_keywords)}")
                    print(distribution_manager.get_summary())
                    break

                print(f"\n🔍 KEYWORD ATTEMPT {keyword_idx}/{len(prioritized_keywords)}: '{keyword}'")
                # Calculate progress dynamically based on keyword completion (10-75% range)
                # This ensures progress never exceeds 100% regardless of keyword count
                progress_percent = 10 + int((keyword_idx / len(prioritized_keywords)) * 65)
                await update_progress(progress_percent, f"Fetching from platforms with keyword '{keyword}'...")

                # Get smart dynamic limits for this keyword based on remaining budget and remaining keywords
                keyword_limits = distribution_manager.get_keyword_limits(keyword_idx, len(prioritized_keywords), enabled_platforms)

                # CONCURRENT FETCHING: Optimize keywords per platform and fetch in parallel
                fetch_tasks = []
                fetch_task_timeouts = []  # Track timeout for each task for accurate error reporting
                social_platform_timeout = 45  # 45 seconds for social platforms
                job_board_timeout = 150  # 150 seconds for job boards (includes scraping + AI analysis for multiple jobs)

                # Twitter - only fetch if limit exists (not at target)
                if BrowsercloudPlatformEnum.TWITTER.value.lower() in enabled_platforms and "twitter" in keyword_limits:
                    twitter_keyword = PlatformKeywordOptimizer.optimize_for_twitter(keyword)
                    twitter_limit = keyword_limits["twitter"]
                    print(f"   🐦 Twitter: '{twitter_keyword}' (max: {twitter_limit} posts)")
                    fetch_tasks.append(
                        asyncio.wait_for(
                            ConversationalLeadJobService._fetch_twitter_leads(
                                twitter_keyword, user_id, lead_form.get("lead_form_id"), lead_form.get("form_title", ""), max_posts=twitter_limit
                            ),
                            timeout=social_platform_timeout
                        )
                    )
                    fetch_task_timeouts.append(social_platform_timeout)
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
                                facebook_keyword, user_id, lead_form.get("lead_form_id"), lead_form.get("form_title", ""), max_posts=facebook_limit
                            ),
                            timeout=social_platform_timeout
                        )
                    )
                    fetch_task_timeouts.append(social_platform_timeout)
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
                                tiktok_keyword, user_id, lead_form.get("lead_form_id"), lead_form.get("form_title", ""), max_posts=tiktok_limit
                            ),
                            timeout=social_platform_timeout
                        )
                    )
                    fetch_task_timeouts.append(social_platform_timeout)
                elif BrowsercloudPlatformEnum.TIKTOK.value.lower() in enabled_platforms:
                    print(f"   🎵 TikTok: SKIPPED (target reached)")

                # PRD Section 5: Job Boards - Use INDEPENDENT job keyword tracking
                if has_job_boards:
                    job_boards_limit = keyword_limits.get("job_boards", 0)

                    # SCENARIO 3: Only job boards - current keyword IS the job keyword
                    # SCENARIO 2: Both social + job - use independent job_keyword_index counter
                    should_fetch_job_boards = False
                    job_keyword_to_use = None

                    if only_job_boards:
                        # SCENARIO 3: Current keyword is a job keyword
                        if keyword in job_board_keywords and job_boards_limit > 0:
                            should_fetch_job_boards = True
                            job_keyword_to_use = keyword
                            job_keyword_attempt = job_board_keywords.index(keyword) + 1
                    else:
                        # SCENARIO 2: Use independent counter for job keywords
                        if job_keyword_index < len(job_board_keywords) and job_boards_limit > 0:
                            should_fetch_job_boards = True
                            job_keyword_to_use = job_board_keywords[job_keyword_index]
                            job_keyword_attempt = job_keyword_index + 1
                            job_keyword_index += 1  # Increment for next iteration

                    if should_fetch_job_boards:
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

                        print(f"   💼 Job Boards: '{job_keyword_to_use}' (Attempt {job_keyword_attempt}/{len(job_board_keywords)}, max: {job_boards_limit} jobs)")

                        if solution_context and solution_context.strip():
                            fetch_tasks.append(
                                asyncio.wait_for(
                                    ConversationalLeadJobService._fetch_job_board_signals(
                                        job_keyword_to_use,
                                        user_id,
                                        lead_form.get("lead_form_id"),
                                        lead_form.get("form_title", ""),
                                        solution_context,
                                        max_jobs=job_boards_limit,
                                        location=lead_form.get("location"),
                                        post_age_filter=lead_form.get("post_age_filter", "all")
                                    ),
                                    timeout=job_board_timeout  # Longer timeout for job scraping + AI analysis
                                )
                            )
                            fetch_task_timeouts.append(job_board_timeout)
                        else:
                            print(f"   ⚠️ Job Boards enabled but no solution_context available (not in form or user onboarding) - skipping")
                    elif has_job_boards and job_boards_limit == 0:
                        print(f"   💼 Job Boards: SKIPPED (100 post target reached)")
                    # If no more job keywords available, silently skip

                # Execute all fetch tasks concurrently
                keyword_leads = []
                platform_errors = []
                platform_successes = 0
                keyword_job_boards_fetched = 0  # Track job boards fetched for THIS keyword only
                keyword_filtered_leads = []  # NEW: Track filtered leads for spam

                if fetch_tasks:
                    print(f"   ⚡ Fetching from {len(fetch_tasks)} platform(s) concurrently...")
                    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                    # Collect successful results and track failures

                    for idx, result in enumerate(results):
                        if isinstance(result, asyncio.TimeoutError):
                            error_msg = f"Platform {idx+1} timed out after {fetch_task_timeouts[idx]}s"
                            print(f"   ⏱️ {error_msg}")
                            platform_errors.append(error_msg)
                        elif isinstance(result, Exception):
                            error_msg = f"Platform {idx+1} error: {str(result)}"
                            print(f"   ❌ {error_msg}")
                            platform_errors.append(error_msg)
                        elif isinstance(result, dict):
                            # Job boards return dict with qualified_leads, filtered_leads, and total_fetched
                            qualified = result.get("qualified_leads", [])
                            filtered = result.get("filtered_leads", [])  # NEW: Get filtered leads
                            total_fetched = result.get("total_fetched", 0)
                            keyword_leads.extend(qualified)
                            keyword_filtered_leads.extend(filtered)  # NEW: Collect filtered
                            job_boards_total_fetched += total_fetched  # Accumulate across all keywords
                            keyword_job_boards_fetched += total_fetched  # Track for THIS keyword only
                            print(f"   ✅ Platform {idx+1} returned {len(qualified)} qualified leads ({total_fetched} total fetched, {len(filtered)} filtered)")
                            platform_successes += 1
                        elif isinstance(result, list):
                            # Social media returns list of leads
                            keyword_leads.extend(result)
                            print(f"   ✅ Platform {idx+1} returned {len(result)} leads")
                            platform_successes += 1

                # If all platforms failed for this keyword, provide helpful message
                if fetch_tasks and platform_successes == 0:
                    print(f"   ⚠️ All {len(fetch_tasks)} platform(s) failed for keyword '{keyword}'")
                    print(f"      Errors: {'; '.join(platform_errors)}")
                elif fetch_tasks and len(keyword_leads) == 0 and platform_successes > 0:
                    print(f"   ℹ️ {platform_successes} platform(s) succeeded but returned 0 results for '{keyword}' - try different keywords or filters")

                # Separate social vs job board leads for stats tracking
                social_batch = [l for l in keyword_leads if l.lead_source != LeadSourceEnum.JOB_BOARDS]
                job_board_batch = [l for l in keyword_leads if l.lead_source == LeadSourceEnum.JOB_BOARDS]

                all_leads.extend(keyword_leads)
                print(f"   📊 Fetched {len(keyword_leads)} raw leads for keyword '{keyword}' (Social: {len(social_batch)}, Job Boards: {len(job_board_batch)})")

                # Update distribution manager counters
                twitter_count = len([l for l in keyword_leads if l.lead_source == LeadSourceEnum.X])
                facebook_count = len([l for l in keyword_leads if l.lead_source == LeadSourceEnum.FACEBOOK])
                tiktok_count = len([l for l in keyword_leads if l.lead_source == LeadSourceEnum.TIKTOK])
                # For job boards: use keyword-specific total_fetched (raw count for THIS keyword only)
                job_boards_count = keyword_job_boards_fetched

                distribution_manager.update_counts(twitter_count, facebook_count, tiktok_count, job_boards_count)

                print(f"   📊 Platform distribution progress:")
                print(f"      Social Media: {distribution_manager.total_social_collected}/{distribution_manager.max_social_posts}")
                print(f"         Twitter:  {distribution_manager.twitter_collected}/{distribution_manager.twitter_target}")
                print(f"         Facebook: {distribution_manager.facebook_collected}/{distribution_manager.facebook_target}")
                print(f"         TikTok:   {distribution_manager.tiktok_collected}/{distribution_manager.tiktok_target}")
                print(f"      Job Boards:   {distribution_manager.job_boards_collected}/{distribution_manager.max_job_posts}")
                print(f"      Grand Total:  {distribution_manager.total_collected}/{distribution_manager.max_total_posts}")

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

                    # Analyze filtered leads (NEW: Use spam-aware method)
                    if leads_after_location_filter:
                        keyword_qualified, keyword_intent_filtered = await ConversationalLeadJobService._analyze_and_filter_leads_with_spam(
                            leads_after_location_filter, category_config, intent_min, relevance_min, final_min
                        )
                        qualified_leads.extend(keyword_qualified)
                        print(f"   ✅ {len(keyword_qualified)} qualified from this keyword ({len(keyword_intent_filtered)} filtered by intent)")
                        print(f"   📈 TOTAL QUALIFIED SO FAR: {len(qualified_leads)}")

                        # === NEW: Save intent-filtered social posts to spam ===
                        if keyword_intent_filtered:
                            try:
                                await ConversationalLeadJobService._save_filtered_to_spam(
                                    db=db,
                                    filtered_leads=keyword_intent_filtered,
                                    user_id=user_id,
                                    lead_form_id=lead_form.get("lead_form_id", ""),
                                    search_keyword=keyword,
                                    filter_stage=SpamFilterStageEnum.INTENT_ANALYSIS.value,
                                    spam_reason=SpamReasonEnum.FAILED_INTENT_ANALYSIS.value,
                                    intent_min=intent_min,
                                    relevance_min=relevance_min,
                                    final_min=final_min,
                                    category_config=category_config
                                )
                            except Exception as spam_error:
                                print(f"   ⚠️ Error saving intent-filtered posts to spam: {str(spam_error)}")
                    else:
                        print(f"   ⚠️ No leads passed filters for this keyword")

                # === NEW: Save filtered job board leads to spam ===
                if keyword_filtered_leads:
                    try:
                        await ConversationalLeadJobService._save_filtered_to_spam(
                            db=db,
                            filtered_leads=keyword_filtered_leads,
                            user_id=user_id,
                            lead_form_id=lead_form.get("lead_form_id", ""),
                            search_keyword=keyword,
                            filter_stage=SpamFilterStageEnum.JOB_BOARD_AI.value,
                            spam_reason=SpamReasonEnum.LOW_COMMERCIAL_RELEVANCE.value,
                            commercial_relevance_threshold=0.3,
                            solution_context=solution_context
                        )
                    except Exception as spam_error:
                        print(f"   ⚠️ Error saving filtered job boards to spam: {str(spam_error)}")

                # Continue with all keywords to maximize results (no early stopping)

            # DYNAMIC KEYWORD EXPANSION: If job boards didn't reach 100 posts, try more keywords
            if has_job_boards and distribution_manager.job_boards_collected < distribution_manager.max_job_posts:
                remaining_needed = distribution_manager.max_job_posts - distribution_manager.job_boards_collected
                print(f"\n💼 Job boards collected {distribution_manager.job_boards_collected}/{distribution_manager.max_job_posts} posts")
                print(f"   📈 Need {remaining_needed} more posts - trying additional keywords...")

                # Get unused keywords (keywords not in the initial 4)
                source_keywords = job_keywords if job_keywords else []
                if only_job_boards:
                    source_keywords = prioritized_keywords  # Use same source as initial selection

                unused_keywords = [k for k in source_keywords if k not in job_board_keywords]

                if unused_keywords and len(unused_keywords) > 0:
                    # Select up to 4 more keywords, but don't exceed total available
                    additional_count = min(4, len(unused_keywords))
                    additional_keywords = random.sample(unused_keywords, additional_count)
                    print(f"   🔑 Trying {len(additional_keywords)} additional keywords: {additional_keywords}")

                    # Fetch from job boards with additional keywords
                    for extra_idx, extra_keyword in enumerate(additional_keywords):
                        # Check for cancellation request
                        if await ConversationalLeadJobService._check_cancellation(db, job_id):
                            print(f"🛑 Job cancelled by user during job boards expansion at keyword {extra_idx + 1}/{len(additional_keywords)}")
                            cancelled_early = True
                            break

                        # Check if we've already reached target
                        if distribution_manager.job_boards_collected >= distribution_manager.max_job_posts:
                            print(f"   ✅ Reached job boards target during expansion - stopping")
                            break

                        print(f"\n🔍 EXPANSION KEYWORD {extra_idx + 1}/{len(additional_keywords)}: '{extra_keyword}'")

                        # Calculate how many more we need
                        job_boards_remaining = distribution_manager.max_job_posts - distribution_manager.job_boards_collected

                        # Fetch from job boards
                        extra_result = await ConversationalLeadJobService._fetch_job_board_signals(
                            extra_keyword,
                            user_id,
                            lead_form.get("lead_form_id"),
                            lead_form.get("form_title", ""),
                            solution_context,
                            max_jobs=job_boards_remaining,
                            location=lead_form.get("location"),
                            post_age_filter=lead_form.get("post_age_filter", "all")
                        )

                        # Extract qualified leads and total fetched from result dict
                        extra_qualified_leads = extra_result.get("qualified_leads", [])
                        extra_total_fetched = extra_result.get("total_fetched", 0)

                        if extra_total_fetched > 0:
                            print(f"   ✅ Got {len(extra_qualified_leads)} qualified job leads from expansion ({extra_total_fetched} total fetched)")

                            # Track total fetched count
                            job_boards_total_fetched += extra_total_fetched

                            # Apply filters to qualified leads
                            post_age_filter = lead_form.get("post_age_filter", "all")
                            location_filter = lead_form.get("location") or []
                            cutoff_date = LeadFilter.calculate_cutoff_date(post_age_filter)

                            filtered_leads = LeadFilter.filter_by_time_range(extra_qualified_leads, cutoff_date)
                            filtered_leads = LeadFilter.filter_by_location(filtered_leads, location_filter)

                            if filtered_leads:
                                all_leads.extend(filtered_leads)
                                qualified_leads.extend(filtered_leads)
                                print(f"   ✅ {len(filtered_leads)} leads passed filters from expansion keyword")

                            # Update distribution manager with TOTAL FETCHED count (not qualified)
                            distribution_manager.update_counts(0, 0, 0, extra_total_fetched)
                            print(f"   📊 Job Boards: {distribution_manager.job_boards_collected}/{distribution_manager.max_job_posts}")
                        else:
                            print(f"   ⚠️ No leads from expansion keyword '{extra_keyword}'")

                    print(f"\n✅ Expansion complete: Job boards now at {distribution_manager.job_boards_collected}/{distribution_manager.max_job_posts}")
                else:
                    print(f"   ⚠️ No unused keywords available for expansion (used all {len(source_keywords)} keywords)")

            # Update statistics - Separate social vs job board leads
            social_all = [l for l in all_leads if l.lead_source != LeadSourceEnum.JOB_BOARDS]
            job_board_all = [l for l in all_leads if l.lead_source == LeadSourceEnum.JOB_BOARDS]

            social_qualified = [l for l in qualified_leads if l.lead_source != LeadSourceEnum.JOB_BOARDS]
            job_board_qualified = [l for l in qualified_leads if l.lead_source == LeadSourceEnum.JOB_BOARDS]

            # Social stats
            stats["social_total_fetched"] = len(social_all)
            stats["social_qualified"] = len(social_qualified)

            # Job board stats
            stats["job_boards_total_fetched"] = job_boards_total_fetched  # Use tracked raw count
            stats["job_signals_found"] = len(job_board_all)  # Job signals after job board AI filter (Stage 1)
            # Count by match strength (from job_board_all, not job_board_qualified)
            for job_lead in job_board_all:
                commercial_relevance = job_lead.commercial_relevance or 0
                if commercial_relevance >= 0.7:
                    stats["job_signals_high_match"] += 1
                elif commercial_relevance >= 0.5:
                    stats["job_signals_medium_match"] += 1
                else:
                    stats["job_signals_low_match"] += 1

            # Combined totals (for backward compatibility)
            stats["total_fetched"] = stats["social_total_fetched"] + stats["job_boards_total_fetched"]
            stats["total_qualified"] = len(qualified_leads)

            print(f"\n✅ INTENT ANALYSIS COMPLETE: {len(qualified_leads)}/{len(all_leads)} leads qualified")
            if len(social_all) > 0:
                print(f"   🔵 Social: {len(social_qualified)}/{len(social_all)} qualified")
            if len(job_board_all) > 0:
                print(f"   💼 Job Boards: {len(job_board_qualified)}/{len(job_board_all)} qualified (High: {stats['job_signals_high_match']}, Medium: {stats['job_signals_medium_match']}, Low: {stats['job_signals_low_match']})")

            # Print final platform distribution summary
            print(distribution_manager.get_summary())

            # Update progress: Analyzing complete, now saving
            await update_progress(80, f"Analyzed {len(all_leads)} posts, saving {len(qualified_leads)} qualified leads...")

            # Save only qualified leads to database
            if qualified_leads:
                await update_progress(85, f"Saving {len(qualified_leads)} qualified leads to database...")
                save_result = await ConversationalLeadJobService._save_leads_batch(db, qualified_leads, lead_form)
                new_count = save_result.get("successful_count", 0)
                duplicate_count = save_result.get("skipped_duplicates", 0)

                # Use accurate per-source breakdown from save_result
                stats["social_new_leads"] = save_result.get("social_new_leads", 0)
                stats["social_duplicates"] = save_result.get("social_duplicates", 0)
                stats["job_signals_saved"] = save_result.get("job_signals_saved", 0)

                # Combined totals
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

        # Check if job was cancelled and handle accordingly
        if job_id and cancelled_early:
            from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository

            await LeadGenerationJobRepository.mark_cancelled(
                db=db,
                job_id=job_id,
                partial_stats=stats,
                processed_count=stats.get("total_fetched", 0)
            )

            print(f"✅ Job {job_id} cancelled successfully")
            print(f"   Partial results: {stats}")

            # Return partial stats (same format as successful completion)
            return stats

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

                # Check if this is a recurring monitoring job (ONLY for conversational leads)
                monitoring_interval_hours = lead_form.get("monitoring_interval_hours", 0)

                if monitoring_interval_hours and monitoring_interval_hours > 0:
                    # Re-queue the job for next monitoring cycle
                    try:
                        from app.services.azure.producers.LeadGenerationProducer import LeadGenerationProducer
                        from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository

                        print(f"🔄 Recurring monitoring enabled: scheduling next run in {monitoring_interval_hours} hour(s)")

                        # Create a NEW job_id for the next monitoring cycle
                        # CRITICAL: Don't reuse the old job_id - workers will skip it as "completed"
                        next_job_id = await LeadGenerationJobRepository.create_job(
                            db=db,
                            lead_form_id=lead_form_id,
                            user_id=user_id,
                            status="queued",
                            progress=0,
                            message=f"Scheduled recurring monitoring (every {monitoring_interval_hours}h)"
                        )

                        # Create a fresh lead_form copy with the NEW job_id
                        next_lead_form = {**lead_form, "job_id": next_job_id}

                        # Schedule the next job execution using Azure Service Bus scheduled messages
                        await LeadGenerationProducer.schedule_lead_generation_job(
                            lead_form_id=lead_form_id,
                            user_id=user_id,
                            lead_form=next_lead_form,  # Use fresh copy with new job_id
                            delay_hours=monitoring_interval_hours
                        )
                        print(f"✅ Next monitoring job {next_job_id} scheduled for {monitoring_interval_hours} hour(s) from now")
                    except Exception as schedule_error:
                        # Don't fail the entire job if scheduling fails
                        print(f"⚠️ Failed to schedule next monitoring job: {schedule_error}")
                        print(f"   Current job completed successfully, but recurring monitoring stopped.")
                else:
                    print(f"✨ One-time execution completed. No recurring monitoring scheduled (monitoring_interval_hours={monitoring_interval_hours}).")
            else:
                print(f"❌ Job {job_id} failed with error: {error_msg}")

        return stats

    @staticmethod
    async def _fetch_twitter_leads(
        search_query: str,
        user_id: str,
        lead_form_id: Optional[str] = None,
        form_title: str = "",
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
                    form_title=form_title,
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
        form_title: str = "",
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
                    form_title=form_title,
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
        form_title: str = "",
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
                    form_title=form_title,
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
        leads: List[LeadCreate],
        lead_form: Optional[Dict] = None
    ) -> Dict:
        """
        Save multiple leads to database, returns statistics with per-source breakdown.

        Returns:
            {
                "successful_count": int,
                "skipped_duplicates": int,
                "social_new_leads": int,
                "social_duplicates": int,
                "job_signals_saved": int,
                "job_signals_duplicates": int
            }
        """
        try:
            # Separate leads by source BEFORE saving
            social_leads = [l for l in leads if l.lead_source != LeadSourceEnum.JOB_BOARDS]
            job_board_leads = [l for l in leads if l.lead_source == LeadSourceEnum.JOB_BOARDS]

            # Generate AI next steps for each lead if goal is provided
            if lead_form and lead_form.get("lead_generation_goal"):
                from app.services.AIService import AIService
                goal = lead_form.get("lead_generation_goal")
                lead_type = str(lead_form.get("form_type", "PERSON"))

                print(f"🎯 Generating next steps for {len(leads)} leads with goal: {goal}")

                # Generate next steps in parallel for all leads
                next_steps_tasks = [
                    AIService.generate_lead_next_steps(
                        lead_data=lead.model_dump() if hasattr(lead, 'model_dump') else lead.dict(),
                        user_goal=goal,
                        lead_type=lead_type
                    )
                    for lead in leads
                ]

                next_steps_results = await asyncio.gather(*next_steps_tasks, return_exceptions=True)

                # Attach next steps to leads
                for idx, next_steps_result in enumerate(next_steps_results):
                    if not isinstance(next_steps_result, Exception) and next_steps_result:
                        leads[idx].ai_next_steps = next_steps_result
                        print(f"✅ Generated {len(next_steps_result.get('steps', []))} steps for lead {idx+1}")
                    else:
                        print(f"⚠️ Failed to generate next steps for lead {idx+1}: {next_steps_result}")

            # Save all leads together
            result = await LeadRepository.multiple_create_leads(db, leads)
            base_result = result.get("responseData", {})

            total_new = base_result.get("successful_count", 0)
            total_duplicates = base_result.get("skipped_duplicates", 0)

            # Calculate accurate breakdown based on actual proportions
            if len(leads) > 0:
                social_proportion = len(social_leads) / len(leads)
                job_proportion = len(job_board_leads) / len(leads)

                # Distribute results proportionally (best approximation without individual tracking)
                social_new = int(total_new * social_proportion)
                social_duplicates = int(total_duplicates * social_proportion)
                job_new = total_new - social_new
                job_duplicates = total_duplicates - social_duplicates
            else:
                social_new = social_duplicates = job_new = job_duplicates = 0

            # Return enhanced stats
            return {
                "successful_count": total_new,
                "skipped_duplicates": total_duplicates,
                "social_new_leads": social_new,
                "social_duplicates": social_duplicates,
                "job_signals_saved": job_new,
                "job_signals_duplicates": job_duplicates
            }
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
        form_title: str = "",
        solution_context: str = "",
        max_jobs: int = 20,
        location: Optional[List[str]] = None,
        post_age_filter: str = "all"
    ) -> Dict[str, Any]:
        """
        Fetch and analyze job postings from LinkedIn Jobs and Jobberman
        Pattern: Same as _fetch_twitter_leads() but for job boards

        Args:
            search_query: Search query for jobs (e.g., "DevOps Engineer")
            user_id: User ID to assign leads to
            lead_form_id: Lead form snapshot ID
            solution_context: User's solution description (for AI analysis)
            max_jobs: Maximum number of jobs to fetch
            location: Location filter list (e.g., ["Lagos", "Nigeria"])
            post_age_filter: Time range filter (e.g., "7d", "30d", "all")

        Returns:
            Dict with:
                - "qualified_leads": List of LeadCreate objects from qualified job postings
                - "total_fetched": Total number of job postings fetched (before AI filtering)
        """
        try:
            print(f"💼 Fetching job board signals with query: '{search_query}'")

            # Import services and helpers
            from app.services.ApifyLinkedInJobsService import ApifyLinkedInJobsService
            from app.services.ApifyJobbermanService import ApifyJobbermanService
            from app.services.ApifyIndeedService import ApifyIndeedService
            from app.services.JobSignalAnalysisService import JobSignalAnalysisService
            from app.services.JobBoardParameterHelper import (
                convert_location_for_job_boards,
                map_post_age_filter
            )

            # Convert location list to Apify-compatible format
            location_str, location_scope = convert_location_for_job_boards(location)

            # Provide contextual feedback based on scope
            if location_scope == "worldwide":
                print(f"   🌍 Searching globally (worldwide jobs)")
                print(f"   ℹ️ TIP: Specify a location for more relevant local opportunities")
            elif location_scope == "country":
                print(f"   🌍 Searching country-wide: {location_str}")
                print(f"   ℹ️ TIP: Add a city for more targeted results")
            elif location_scope == "city":
                print(f"   📍 Searching location: {location_str}")
                if location and len(location) > 1:
                    print(f"   ℹ️ Additional locations for filtering: {', '.join(location[1:])}")

            # Map post age filter to platform-specific formats
            published_at_linkedin = map_post_age_filter(post_age_filter, "linkedin")
            posted_date_jobberman = map_post_age_filter(post_age_filter, "jobberman")

            print(f"   📅 Time filter: {post_age_filter} (LinkedIn: {published_at_linkedin}, Jobberman: {posted_date_jobberman})")

            # Initialize services
            linkedin_service = ApifyLinkedInJobsService()
            jobberman_service = ApifyJobbermanService()
            indeed_service = ApifyIndeedService()

            # PRD: Fetch from LinkedIn Jobs, Jobberman, and Indeed CONCURRENTLY (parallel)
            # Distribute max_jobs: 50% LinkedIn, 25% Jobberman, 25% Indeed
            linkedin_max = max(1, int(max_jobs * 0.50))   # 50%
            jobberman_max = max(1, int(max_jobs * 0.25))  # 25%
            indeed_max = max(1, int(max_jobs * 0.25))     # 25%

            print(f"   💼 Distributing {max_jobs} jobs: LinkedIn {linkedin_max}, Jobberman {jobberman_max}, Indeed {indeed_max}")
            print(f"   ⚡ Fetching from all 3 job boards in parallel...")

            # Fetch from all 3 services concurrently (3x speedup!)
            results = await asyncio.gather(
                linkedin_service.fetch_job_postings(
                    search_query,
                    max_jobs=linkedin_max,
                    location=location_str,  # None if worldwide
                    published_at=published_at_linkedin,
                    solution_context=solution_context
                ),
                jobberman_service.fetch_job_postings(
                    search_query,
                    max_jobs=jobberman_max,
                    location=location_str,
                    posted_date=posted_date_jobberman
                ) if location_str else {"success": True, "jobs": [], "total_jobs": 0},  # Skip Jobberman if no location
                indeed_service.fetch_job_postings(
                    search_query,
                    max_jobs=indeed_max
                ),
                return_exceptions=True  # Don't fail all if one fails
            )

            # Log if Jobberman was skipped
            if not location_str:
                print(f"   ⚠️ Skipping Jobberman (requires specific location for relevant results)")

            # Unpack results
            linkedin_result = results[0] if not isinstance(results[0], Exception) else {"success": False, "jobs": [], "error": str(results[0])}
            jobberman_result = results[1] if not isinstance(results[1], Exception) else {"success": False, "jobs": [], "error": str(results[1])}
            indeed_result = results[2] if not isinstance(results[2], Exception) else {"success": False, "jobs": [], "error": str(results[2])}

            # Log errors if any
            if isinstance(results[0], Exception):
                print(f"   ⚠️ LinkedIn error: {str(results[0])}")
            if isinstance(results[1], Exception):
                print(f"   ⚠️ Jobberman error: {str(results[1])}")
            if isinstance(results[2], Exception):
                print(f"   ⚠️ Indeed error: {str(results[2])}")

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

            print(f"   ✅ Found {len(all_jobs)} total job postings (LinkedIn: {len(linkedin_result.get('jobs', []))}, Jobberman: {len(jobberman_result.get('jobs', []))}, Indeed: {len(indeed_result.get('jobs', []))})")

            if not all_jobs:
                print(f"   ⚠️ No jobs found for query '{search_query}'")
                return []

            # Deduplicate jobs (same company + similar title)
            deduplicated_jobs = ConversationalLeadJobService._deduplicate_jobs(all_jobs)
            print(f"   After deduplication: {len(deduplicated_jobs)} unique jobs")

            # Analyze each job posting with AI
            qualified_signals = []
            filtered_signals = []  # NEW: Collect filtered jobs for spam

            for job in deduplicated_jobs[:max_jobs]:  # Limit to max_jobs
                try:
                    # Run AI analysis
                    analysis = await JobSignalAnalysisService.analyze_job_posting(
                        job_description=job.get("description", ""),
                        job_title=job.get("title", ""),
                        company_name=job.get("company", ""),
                        solution_context=solution_context
                    )

                    # Create lead object (same for both qualified and filtered)
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
                        form_title=form_title,
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
                        location=job.get("location", ""),  # Add location
                    )

                    # Filter by commercial_relevance threshold (PRD requirement: >= 0.3)
                    if analysis.commercial_relevance >= 0.3:
                        qualified_signals.append(lead)
                        print(f"   ✅ QUALIFIED: {job.get('company')} - {job.get('title')} | Match:{analysis.problem_solution_match:.2f} Relevance:{analysis.commercial_relevance:.2f}")
                    else:
                        # NEW: Collect filtered job for spam
                        filtered_signals.append(lead)
                        print(f"   ❌ FILTERED: {job.get('company')} - {job.get('title')} | Relevance:{analysis.commercial_relevance:.2f} (below 0.3 threshold)")

                except Exception as analysis_error:
                    print(f"   ⚠️ Error analyzing job {job.get('title')}: {str(analysis_error)}")
                    continue

            print(f"   ✅ {len(qualified_signals)} qualified job signals (from {len(deduplicated_jobs)} analyzed)")

            # NEW: Return filtered signals for spam saving
            # This will be passed back to the caller

            # Return both total fetched and qualified leads
            # Counter will use total_fetched to track raw posts (like social media)
            return {
                "qualified_leads": qualified_signals,
                "filtered_leads": filtered_signals,  # NEW: Include filtered for spam
                "total_fetched": len(deduplicated_jobs)
            }

        except Exception as e:
            print(f"❌ Error fetching job board signals: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"qualified_leads": [], "filtered_leads": [], "total_fetched": 0}

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

    # ============================================
    # SPAM FEATURE METHODS (NEW - for spam visibility)
    # PRD: Lead Gen Enhancement - Spam Visibility Feature
    # These methods DO NOT modify existing lead generation logic
    # ============================================

    @staticmethod
    async def _save_filtered_to_spam(
        db: AsyncIOMotorDatabase,
        filtered_leads: List[LeadCreate],
        user_id: str,
        lead_form_id: str,
        search_keyword: str,
        filter_stage: str,
        spam_reason: str,
        **context
    ) -> None:
        """
        NEW METHOD - Save filtered leads to spam collection

        PRD Section 3.4: Each spam item must display reason for disqualification
        PRD Section 4.7: Spam scoped per lead form

        This method does NOT interfere with existing qualified lead logic.
        It only saves filtered-out items to a separate spam collection.

        Args:
            db: Database connection
            filtered_leads: List of LeadCreate objects that failed filters
            user_id: User ID
            lead_form_id: Lead form snapshot ID (for scoping per form)
            search_keyword: Keyword that fetched these leads
            filter_stage: "job_board_ai" | "intent_analysis" | "time_filter" | "location_filter"
            spam_reason: Primary spam reason (from SpamReasonEnum)
            **context: Additional context (scores, thresholds, category_config, etc.)

        Returns:
            None (saves to spam collection)
        """
        if not filtered_leads:
            return

        spam_leads = []

        for lead in filtered_leads:
            # Build spam lead based on filter stage
            spam_lead_data = {
                "user_id": user_id,
                "original_lead_data": lead.dict(),
                "spam_reason": spam_reason,
                "filter_stage": filter_stage,
                "search_keyword": search_keyword,
                "lead_form_snapshot_id": lead_form_id,
                "lead_source": lead.lead_source,
                "content_full": lead.mention,
                "content_preview": lead.mention[:300] if lead.mention else None,
            }

            # === JOB BOARD SPECIFIC FIELDS ===
            if lead.lead_source == LeadSourceEnum.JOB_BOARDS:
                spam_lead_data.update({
                    "platform_detail": lead.job_source,
                    "problem_solution_match": lead.problem_solution_match,
                    "hiring_intent_score": lead.hiring_intent_score,
                    "commercial_relevance": lead.commercial_relevance,
                    "company_confidence": lead.company_confidence,
                    "implied_problems": lead.implied_problems,
                    "job_board_reasoning": getattr(lead, "reasoning", None),
                    "job_posting_url": lead.job_posting_url,
                    "job_title": lead.job_title_field,
                    "hiring_company": lead.hiring_company,
                    "job_source": lead.job_source,
                    "display_title": lead.job_title_field,
                    "display_company": lead.hiring_company,
                    "display_username": lead.hiring_company,
                    "display_link": lead.job_posting_url,
                    "display_source": lead.job_source or "Job Boards",
                    "display_location": lead.location,
                })

                # Add thresholds from context
                if "commercial_relevance_threshold" in context:
                    spam_lead_data["commercial_relevance_threshold"] = context["commercial_relevance_threshold"]

                # Add solution context
                if "solution_context" in context:
                    spam_lead_data["solution_context"] = context["solution_context"]

                # Build detailed reason for job boards
                spam_lead_data["spam_reason_detail"] = (
                    f"Commercial relevance ({lead.commercial_relevance:.2f}) "
                    f"below threshold ({context.get('commercial_relevance_threshold', 0.3)})"
                )

            # === SOCIAL POST SPECIFIC FIELDS ===
            else:
                spam_lead_data.update({
                    "intent_score": lead.intent_score,
                    "relevance_score": lead.relevance_score,
                    "final_score": lead.final_score,
                    "urgency_flag": lead.urgency_flag,
                    "sentiment": lead.sentiment.value if lead.sentiment else None,
                    "intent_category": lead.intent_category.value if lead.intent_category else None,
                    "intent_reasoning": lead.intent_reasoning,
                    "post_author": lead.username,
                    "post_url": lead.lead_link,
                    "social_profile": lead.social_profile_link,
                    "display_title": lead.mention[:100] if lead.mention else "No content",
                    "display_username": lead.username,
                    "display_link": lead.lead_link,
                    "display_source": lead.lead_source,
                    "display_location": lead.location,
                })

                # Add thresholds from context
                if "intent_min" in context:
                    spam_lead_data["intent_min_threshold"] = context["intent_min"]
                if "relevance_min" in context:
                    spam_lead_data["relevance_min_threshold"] = context["relevance_min"]
                if "final_min" in context:
                    spam_lead_data["final_min_threshold"] = context["final_min"]

                # Add category config from context
                if "category_config" in context:
                    cat_config = context["category_config"]
                    spam_lead_data.update({
                        "search_category": cat_config.category_context,
                        "category_keywords": cat_config.keywords,
                        "buying_signals": cat_config.buying_signals,
                        "excluded_keywords": cat_config.excluded_keywords,
                    })

                # Build detailed reason for social posts
                failed_criteria = []
                if lead.intent_score and lead.intent_score < context.get("intent_min", 0.5):
                    failed_criteria.append(f"intent ({lead.intent_score:.2f} < {context.get('intent_min', 0.5)})")
                if lead.relevance_score and lead.relevance_score < context.get("relevance_min", 0.45):
                    failed_criteria.append(f"relevance ({lead.relevance_score:.2f} < {context.get('relevance_min', 0.45)})")
                if lead.final_score and lead.final_score < context.get("final_min", 0.55):
                    failed_criteria.append(f"final ({lead.final_score:.2f} < {context.get('final_min', 0.55)})")

                spam_lead_data["spam_reason_detail"] = f"Failed: {', '.join(failed_criteria)}" if failed_criteria else "Failed intent qualification"

            # Add time filter context if provided
            if "post_created_date" in context:
                spam_lead_data["post_created_date"] = lead.created_date
            if "cutoff_date" in context:
                spam_lead_data["cutoff_date"] = context["cutoff_date"]
            if "post_age_filter" in context:
                spam_lead_data["post_age_filter"] = context["post_age_filter"]

            # Add location filter context if provided
            if "target_locations" in context:
                spam_lead_data["target_locations"] = context["target_locations"]
                spam_lead_data["post_location"] = lead.location

            # Create spam lead object
            spam_lead = SpamLeadCreate(**spam_lead_data)
            spam_leads.append(spam_lead)

        # Save to spam collection
        await SpamLeadRepository.save_spam_leads_batch(db, spam_leads)
        print(f"💾 SPAM: Saved {len(spam_leads)} filtered leads to spam collection (reason: {spam_reason})")

    @staticmethod
    async def _analyze_single_lead_with_spam(
        lead: LeadCreate,
        category_config: CategoryConfig,
        intent_min: float,
        relevance_min: float,
        final_min: float
    ) -> tuple[LeadCreate, bool, str]:
        """
        NEW METHOD - Analyze lead and return it WITH scores regardless of qualification

        Unlike _analyze_single_lead which returns None for filtered leads,
        this method ALWAYS returns the lead with scores populated.

        Args:
            lead: LeadCreate object
            category_config: Category configuration
            intent_min, relevance_min, final_min: Thresholds

        Returns:
            Tuple of (lead_with_scores, is_qualified, status_message)
        """
        try:
            # Get post text from mention field
            post_text = lead.mention or lead.lead_reason or ""
            if not post_text.strip():
                return lead, False, f"Skipping {lead.username}: no text content"

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

            # Map enums
            intent_category_map = {
                "direct": IntentCategoryEnum.DIRECT,
                "implied": IntentCategoryEnum.IMPLIED,
                "problem": IntentCategoryEnum.PROBLEM,
                "comparison": IntentCategoryEnum.COMPARISON,
                "competitor_negative": IntentCategoryEnum.COMPETITOR_NEGATIVE,
                "unknown": IntentCategoryEnum.UNKNOWN
            }

            sentiment_map = {
                "positive": SentimentTypeEnum.POSITIVE,
                "negative": SentimentTypeEnum.NEGATIVE,
                "neutral": SentimentTypeEnum.NEUTRAL
            }

            # Populate intent fields in lead (ALWAYS, even if filtered)
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
                status = f"✅ QUALIFIED: {lead.username} | Intent:{intent_result.intent_score:.2f} Relevance:{intent_result.relevance_score:.2f} Final:{final_score:.2f}"
            else:
                status = f"❌ FILTERED: {lead.username} | Intent:{intent_result.intent_score:.2f} Relevance:{intent_result.relevance_score:.2f} Final:{final_score:.2f}"

            return lead, is_qualified, status

        except Exception as e:
            error_msg = f"Error analyzing lead {lead.username}: {str(e)}"
            return lead, False, error_msg

    @staticmethod
    async def _analyze_and_filter_leads_with_spam(
        leads: List[LeadCreate],
        category_config: CategoryConfig,
        intent_min: float = 0.50,
        relevance_min: float = 0.45,
        final_min: float = 0.55
    ) -> tuple[List[LeadCreate], List[LeadCreate]]:
        """
        NEW METHOD - Analyze leads and return BOTH qualified and filtered lists

        Uses _analyze_single_lead_with_spam to get all leads with scores.

        Args:
            leads: List of LeadCreate objects
            category_config: Category configuration for intent analysis
            intent_min, relevance_min, final_min: Qualification thresholds

        Returns:
            Tuple of (qualified_leads, filtered_leads)
            Both lists have intent scores populated
        """
        if not leads:
            return [], []

        print(f"📊 INTENT ANALYSIS (with spam): Analyzing {len(leads)} posts in parallel...")

        # Process all leads in parallel
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                ConversationalLeadJobService._llm_executor,
                lambda l=lead: asyncio.run(
                    ConversationalLeadJobService._analyze_single_lead_with_spam(
                        l, category_config, intent_min, relevance_min, final_min
                    )
                )
            )
            for lead in leads
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate qualified and filtered
        qualified_leads = []
        filtered_leads = []

        for result in results:
            if isinstance(result, Exception):
                print(f"Exception during analysis: {str(result)}")
                continue

            lead, is_qualified, status = result
            print(status)

            if is_qualified:
                qualified_leads.append(lead)
            else:
                # NEW: Collect filtered lead with scores
                filtered_leads.append(lead)

        # Handle adaptive thresholds (same as existing method)
        if len(qualified_leads) == 0 and len(leads) > 0:
            print(f"⚠️ Zero leads qualified with default thresholds. Trying relaxed thresholds...")

            relaxed_intent = intent_min - 0.10
            relaxed_relevance = relevance_min - 0.10
            relaxed_final = final_min - 0.10

            print(f"   Default: intent>={intent_min}, relevance>={relevance_min}, final>={final_min}")
            print(f"   Relaxed: intent>={relaxed_intent}, relevance>={relaxed_relevance}, final>={relaxed_final}")

            # Re-check filtered leads with relaxed thresholds
            # Leads that pass relaxed get promoted to qualified
            relaxed_qualified = []
            still_filtered = []
            for lead in filtered_leads:
                if lead is None:
                    continue
                if ((lead.intent_score or 0) >= relaxed_intent and
                    (lead.relevance_score or 0) >= relaxed_relevance and
                    (lead.final_score or 0) >= relaxed_final):
                    relaxed_qualified.append(lead)
                else:
                    still_filtered.append(lead)

            if len(relaxed_qualified) > 0:
                print(f"✅ Found {len(relaxed_qualified)} leads with relaxed thresholds")
                qualified_leads = relaxed_qualified
                filtered_leads = still_filtered

        return qualified_leads, filtered_leads
