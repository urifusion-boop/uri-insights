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
from app.repository.LeadRepository import LeadRepository
from app.domain.schemas.lead_schema import LeadCreate
from app.domain.enums.lead_enum import LeadSourceEnum, LeadStatusEnum, LeadOpportunityTypeEnum
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

            # Save all leads to database
            if all_leads:
                await ConversationalLeadJobService._save_leads_batch(db, all_leads)
                print(f"Successfully saved {len(all_leads)} leads from {len(enabled_platforms)} platform(s)")
            else:
                print(f"No leads found for keyword '{keyword}' across enabled platforms")

        except Exception as e:
            print(f"Error in fetch_leads_from_platforms: {str(e)}")
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
    def _convert_twitter_date(twitter_date: str) -> datetime:
        """Convert Twitter date format to datetime"""
        try:
            # Twitter format: "Sun Nov 09 17:51:05 +0000 2025"
            return datetime.strptime(twitter_date, "%a %b %d %H:%M:%S %z %Y")
        except Exception as e:
            print(f"Error converting Twitter date '{twitter_date}': {str(e)}")
            return datetime.utcnow()
