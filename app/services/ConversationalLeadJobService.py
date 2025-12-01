"""
ConversationalLeadJobService.py
Background job service for fetching leads from Twitter, Facebook, and TikTok
when a conversational lead form is created or updated.
"""
import asyncio
import time
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
    ) -> Dict:
        """
        Fetch leads from all enabled platforms in the lead form configuration.
        This runs as a background job immediately after form save/update.

        Args:
            db: MongoDB database instance
            lead_form: The lead form document containing platform configs and keywords
            user_id: User ID to assign leads to

        Returns:
            Dict with statistics: total_fetched, total_qualified, new_leads_saved, duplicates_skipped
        """
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
            print(f"📋 Enabled platforms: {list(enabled_platforms.keys())}")
            print(f"   Checking for Twitter: '{BrowsercloudPlatformEnum.TWITTER.value}'")
            print(f"   Checking for Facebook: '{BrowsercloudPlatformEnum.FACEBOOK.value}'")
            print(f"   Checking for TikTok: '{BrowsercloudPlatformEnum.TIKTOK.value}'")

            # Use first keyword for search (proven to work better than OR combinations)
            keyword = all_search_keywords[0] if all_search_keywords else ""
            print(f"🔍 Using primary search keyword: '{keyword}'")

            # Fetch leads from each platform
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

            # Update statistics
            stats["total_fetched"] = len(all_leads)

            # Analyze leads for intent and filter qualified ones
            if all_leads:

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

                stats["total_qualified"] = len(qualified_leads)
                print(f"✅ INTENT ANALYSIS COMPLETE: {len(qualified_leads)}/{len(all_leads)} leads qualified")

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
            else:
                print(f"No leads found for keyword '{keyword}' across enabled platforms")

        except Exception as e:
            import traceback
            print(f"❌ ERROR in fetch_leads_from_platforms: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            search_success = False
            error_msg = str(e)
            # Don't raise - this is a background job, we just log the error

        # Calculate duration
        duration = time.time() - start_time

        # Save search history
        try:
            search_history = LeadSearchHistoryCreate(
                user_id=user_id,
                lead_form_id=lead_form.get("lead_form_id", ""),
                lead_form_name=lead_form.get("form_title", ""),
                keyword=", ".join(all_search_keywords[:3]) + ("..." if len(all_search_keywords) > 3 else ""),  # Show first 3 keywords
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
            response = await twitter_service.fetch_tweets_with_analysis(search_query, max_tweets=10, analyze_sentiment=False)
            print(f"   Twitter API response success: {response.get('success')}")
            tweets = response.get("tweets", [])
            print(f"   Found {len(tweets)} tweets")

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
            response = await facebook_service.fetch_posts_with_analysis(search_query, max_posts=10, analyze_sentiment=False)
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
            response = await tiktok_service.fetch_posts_with_analysis(search_query, max_posts=10, analyze_sentiment=False)
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

        return CategoryConfig(
            category_context=category_context,
            keywords=keywords,
            implied_keywords=implied_keywords,
            competitors=competitors,
            buying_signals=buying_signals,
            excluded_keywords=excluded_keywords
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
        intent_min: float = 0.55,
        relevance_min: float = 0.50,
        final_min: float = 0.60
    ) -> List[LeadCreate]:
        """
        Analyze all leads for buying intent in parallel and filter to qualified leads only

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
