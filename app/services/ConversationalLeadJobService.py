"""
ConversationalLeadJobService.py
Background job service for fetching leads from Twitter, Facebook, and TikTok
when a conversational lead form is created or updated.
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.TwitterService import TwitterService
from app.services.FacebookService import FacebookService
from app.services.TiktokService import TiktokService
from app.services.IntentAnalysisService import IntentAnalysisService, CategoryConfig
from app.repository.LeadRepository import LeadRepository
from app.domain.schemas.lead_schema import LeadCreate
from app.domain.enums.lead_enum import LeadSourceEnum, LeadStatusEnum, LeadOpportunityTypeEnum, IntentCategoryEnum, SentimentTypeEnum
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.domain.schemas.browsercloud_schema import BrowsercloudPlatformEnum


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
    ):
        """
        Fetch leads from all enabled platforms in the lead form configuration.
        This runs as a background job immediately after form save/update.

        Args:
            db: MongoDB database instance
            lead_form: The lead form document containing platform configs and keywords
            user_id: User ID to assign leads to
        """
        try:
            print(f"🚀 BACKGROUND JOB STARTED: Fetching leads for form {lead_form.get('lead_form_id')}")
            print(f"   Platform configs: {lead_form.get('platform_configs', [])}")
            print(f"   Keywords: {lead_form.get('keywords', [])}")
        except Exception as log_error:
            print(f"Error in initial logging: {str(log_error)}")

        try:
            platform_configs = lead_form.get("platform_configs", [])
            keywords = lead_form.get("keywords", [])

            if not keywords or len(keywords) == 0:
                print(f"No keywords provided for lead form {lead_form.get('lead_form_id')}")
                return

            # Use first keyword for fetching (can be enhanced to use multiple keywords)
            keyword = keywords[0]

            # Collect all enabled platforms
            enabled_platforms = {
                config.get("platform"): config
                for config in platform_configs
                if config.get("enabled", False)
            }

            if not enabled_platforms:
                print(f"No enabled platforms for lead form {lead_form.get('lead_form_id')}")
                return

            all_leads: List[LeadCreate] = []

            # TODO: Uncomment below for concurrent fetching in production
            # # Create tasks for concurrent fetching
            # fetch_tasks = []
            #
            # if BrowsercloudPlatformEnum.TWITTER.value in enabled_platforms:
            #     fetch_tasks.append(
            #         ConversationalLeadJobService._fetch_twitter_leads(
            #             keyword, user_id, lead_form.get("lead_form_id")
            #         )
            #     )
            #
            # if BrowsercloudPlatformEnum.FACEBOOK.value in enabled_platforms:
            #     fetch_tasks.append(
            #         ConversationalLeadJobService._fetch_facebook_leads(
            #             keyword, user_id, lead_form.get("lead_form_id")
            #         )
            #     )
            #
            # if BrowsercloudPlatformEnum.TIKTOK.value in enabled_platforms:
            #     fetch_tasks.append(
            #         ConversationalLeadJobService._fetch_tiktok_leads(
            #             keyword, user_id, lead_form.get("lead_form_id")
            #         )
            #     )
            #
            # # Execute all fetch tasks concurrently
            # if fetch_tasks:
            #     results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            #
            #     # Collect successful results
            #     for result in results:
            #         if isinstance(result, list):
            #             all_leads.extend(result)
            #         elif isinstance(result, Exception):
            #             print(f"Error fetching leads: {str(result)}")

            # TEMPORARY: Sequential fetching (replace with concurrent version above later)
            # Fetch Twitter leads
            if BrowsercloudPlatformEnum.TWITTER.value in enabled_platforms:
                try:
                    twitter_leads = await ConversationalLeadJobService._fetch_twitter_leads(
                        keyword, user_id, lead_form.get("lead_form_id")
                    )
                    all_leads.extend(twitter_leads)
                    print(f"Fetched {len(twitter_leads)} leads from Twitter")
                except Exception as e:
                    print(f"Error fetching Twitter leads: {str(e)}")

            # Fetch Facebook leads
            if BrowsercloudPlatformEnum.FACEBOOK.value in enabled_platforms:
                try:
                    facebook_leads = await ConversationalLeadJobService._fetch_facebook_leads(
                        keyword, user_id, lead_form.get("lead_form_id")
                    )
                    all_leads.extend(facebook_leads)
                    print(f"Fetched {len(facebook_leads)} leads from Facebook")
                except Exception as e:
                    print(f"Error fetching Facebook leads: {str(e)}")

            # Fetch TikTok leads
            if BrowsercloudPlatformEnum.TIKTOK.value in enabled_platforms:
                try:
                    tiktok_leads = await ConversationalLeadJobService._fetch_tiktok_leads(
                        keyword, user_id, lead_form.get("lead_form_id")
                    )
                    all_leads.extend(tiktok_leads)
                    print(f"Fetched {len(tiktok_leads)} leads from TikTok")
                except Exception as e:
                    print(f"Error fetching TikTok leads: {str(e)}")

            # Analyze leads for intent and filter qualified ones
            if all_leads:
                print(f"📊 INTENT ANALYSIS: Analyzing {len(all_leads)} posts for buying intent...")

                # Build category configuration from lead form
                category_config = ConversationalLeadJobService._build_category_config(lead_form)

                # Get custom scoring thresholds if specified
                scoring_thresholds = lead_form.get("scoring_thresholds", {})
                intent_min = scoring_thresholds.get("intent_score_min", 0.55)
                relevance_min = scoring_thresholds.get("relevance_score_min", 0.50)
                final_min = scoring_thresholds.get("final_score_min", 0.60)

                # Analyze all leads with intent scoring
                qualified_leads = await ConversationalLeadJobService._analyze_and_filter_leads(
                    all_leads, category_config, intent_min, relevance_min, final_min
                )

                print(f"✅ INTENT ANALYSIS COMPLETE: {len(qualified_leads)}/{len(all_leads)} leads qualified")

                # Save only qualified leads to database
                if qualified_leads:
                    await ConversationalLeadJobService._save_leads_batch(db, qualified_leads)
                    print(f"Successfully saved {len(qualified_leads)} qualified leads from {len(enabled_platforms)} platform(s)")
                else:
                    print(f"No qualified leads found after intent analysis")
            else:
                print(f"No leads found for keyword '{keyword}' across enabled platforms")

        except Exception as e:
            import traceback
            print(f"❌ ERROR in fetch_leads_from_platforms: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            # Don't raise - this is a background job, we just log the error

    @staticmethod
    async def _fetch_twitter_leads(
        keyword: str,
        user_id: str,
        lead_form_id: Optional[str] = None
    ) -> List[LeadCreate]:
        """Fetch leads from Twitter"""
        try:
            response = await TwitterService.fetch_twitter_search(keyword, limit=10)
            tweets = response.get("responseData", {}).get("tweets", [])

            leads = []
            for tweet in tweets:
                lead = LeadCreate(
                    first_name=tweet.get("author", "Twitter User"),
                    last_name="",
                    username=tweet.get("author", ""),
                    mention=tweet.get("text", ""),
                    lead_reason=tweet.get("text", ""),
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
                )

                # Add sentiment and confidence if available
                if "sentiment" in tweet:
                    lead.notes = f"Sentiment: {tweet['sentiment']}"
                if "confidence" in tweet:
                    lead.score = int(float(tweet.get("confidence", 0)) * 100)

                leads.append(lead)

            return leads
        except Exception as e:
            print(f"Error fetching Twitter leads: {str(e)}")
            return []

    @staticmethod
    async def _fetch_facebook_leads(
        keyword: str,
        user_id: str,
        lead_form_id: Optional[str] = None
    ) -> List[LeadCreate]:
        """Fetch leads from Facebook"""
        try:
            response = await FacebookService.fetch_posts(keyword, limit=10)
            posts = (
                response.get("responseData", {}).get("posts", [])
                or response.get("responseData", {}).get("data", {}).get("posts", [])
            )

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

                lead = LeadCreate(
                    first_name=post.get("author", "Facebook User"),
                    last_name="",
                    username=post.get("author", ""),
                    mention=post.get("text", ""),
                    lead_reason=post.get("text", ""),
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
                )

                # Add sentiment and confidence if available
                if "sentiment" in post:
                    lead.notes = f"Sentiment: {post['sentiment']}"
                if "confidence" in post:
                    lead.score = int(float(post.get("confidence", 0)) * 100)

                leads.append(lead)

            return leads
        except Exception as e:
            print(f"Error fetching Facebook leads: {str(e)}")
            return []

    @staticmethod
    async def _fetch_tiktok_leads(
        keyword: str,
        user_id: str,
        lead_form_id: Optional[str] = None
    ) -> List[LeadCreate]:
        """Fetch leads from TikTok"""
        try:
            response = await TiktokService.fetch_posts(keyword, limit=10)
            posts = (
                response.get("responseData", {}).get("posts", [])
                or response.get("responseData", {}).get("data", {}).get("posts", [])
            )

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

                lead = LeadCreate(
                    first_name=post.get("author") or post.get("username", "TikTok User"),
                    last_name="",
                    username=post.get("author") or post.get("username", ""),
                    mention=post.get("text") or post.get("desc", ""),
                    lead_reason=post.get("text") or post.get("desc", ""),
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
                )

                # Add sentiment and confidence if available
                if "sentiment" in post:
                    lead.notes = f"Sentiment: {post['sentiment']}"
                if "confidence" in post:
                    lead.score = int(float(post.get("confidence", 0)) * 100)

                leads.append(lead)

            return leads
        except Exception as e:
            print(f"Error fetching TikTok leads: {str(e)}")
            return []

    @staticmethod
    async def _save_leads_batch(
        db: AsyncIOMotorDatabase,
        leads: List[LeadCreate]
    ):
        """Save multiple leads to database"""
        try:
            for lead in leads:
                await LeadRepository.create(db, lead)
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

        return CategoryConfig(
            category_context=category_context,
            keywords=keywords,
            implied_keywords=implied_keywords,
            competitors=competitors,
            buying_signals=buying_signals,
            excluded_keywords=excluded_keywords
        )

    @staticmethod
    async def _analyze_and_filter_leads(
        leads: List[LeadCreate],
        category_config: CategoryConfig,
        intent_min: float = 0.55,
        relevance_min: float = 0.50,
        final_min: float = 0.60
    ) -> List[LeadCreate]:
        """
        Analyze all leads for buying intent and filter to qualified leads only

        Args:
            leads: List of LeadCreate objects
            category_config: Category configuration for intent analysis
            intent_min, relevance_min, final_min: Qualification thresholds

        Returns:
            List of qualified LeadCreate objects with intent scores populated
        """
        if not leads:
            return []

        qualified_leads = []

        # Analyze each lead for intent
        for lead in leads:
            try:
                # Get post text from mention field
                post_text = lead.mention or lead.lead_reason or ""
                if not post_text.strip():
                    print(f"Skipping lead with no text content")
                    continue

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
                if (
                    intent_result.intent_score >= intent_min and
                    intent_result.relevance_score >= relevance_min and
                    final_score >= final_min
                ):
                    qualified_leads.append(lead)
                    print(f"✅ QUALIFIED: {lead.username} | Intent:{intent_result.intent_score:.2f} Relevance:{intent_result.relevance_score:.2f} Final:{final_score:.2f}")
                else:
                    print(f"❌ FILTERED: {lead.username} | Intent:{intent_result.intent_score:.2f} Relevance:{intent_result.relevance_score:.2f} Final:{final_score:.2f}")

            except Exception as e:
                print(f"Error analyzing lead {lead.username}: {str(e)}")
                # Skip leads that fail analysis
                continue

        return qualified_leads

    @staticmethod
    def _convert_twitter_date(twitter_date: str) -> datetime:
        """Convert Twitter date format to datetime"""
        try:
            # Twitter format: "Sun Nov 09 17:51:05 +0000 2025"
            return datetime.strptime(twitter_date, "%a %b %d %H:%M:%S %z %Y")
        except Exception as e:
            print(f"Error converting Twitter date '{twitter_date}': {str(e)}")
            return datetime.utcnow()
