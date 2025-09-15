from datetime import datetime, timedelta
from typing import Any, List
from app.core.helpers.facebook_helper import FacebookHelper
from app.core.helpers.instagram_helper import InstagramHelper
from app.core.helpers.linkedin_helper import LinkedinHelper
from app.core.helpers.tiktok_helper import TiktokHelper
from app.core.helpers.twitter_helper import TwitterHelper
from app.domain.enums.linkedin_enum import (
    LinkedInTokenScopeEnum,
    LinkedinUrnNamespaceEnum,
)
from app.domain.enums.socialmediapost_enum import PostStatusEnum, PostTypeEnum
from app.domain.schemas.socialmediapost_schema import SocialMediaPost
from app.repository.InfluencerRepository import InfluencerRepository
from app.repository.SocialMediaPostRepository import SocialMediaPostRepository
from app.services.FacebookService import FacebookService
from app.services.InstagramService import InstagramService
from app.services.LinkedInManageShareService import LinkedInManageShareService
from app.services.LinkedInService import LinkedInService
from app.services.TiktokService import TiktokService
from app.services.XManageTweetService import XManageTweetService
from motor.motor_asyncio import AsyncIOMotorDatabase


class SocialMediaPostService:
    @staticmethod
    async def post_scheduled_posts(db: AsyncIOMotorDatabase):
        print("Running background job")
        scheduled_posts: List[SocialMediaPost] = (
            await SocialMediaPostService.get_all_scheduled_posts(db)
        )

        try:
            for post in scheduled_posts:
                # Check if the post is due for LinkedIn, TikTok, or Facebook
                if post["platform"] in ["LINKEDIN", "TIKTOK", "FACEBOOK", "INSTAGRAM"]:
                    print("\nPost data is due: ", post)
                    if SocialMediaPostService.__check_if_scheduled_post_is_due(post):
                        await SocialMediaPostService.post_scheduled_post(
                            db, post, post["platform"]
                        )
            print("\nBackground job ran successfully")
        except Exception as e:
            print("\nError running background job: ", e)

    @staticmethod
    def __check_if_scheduled_post_is_due(post_data: dict) -> bool:
        """
        Check if a Facebook post is scheduled to be published by comparing the combined date and time
        against the current datetime.

        Args:
            post_data (dict): A dictionary containing the post's "start_date" and "start_time".

        Returns:
            bool: True if the post is due to be published, False otherwise.
        """
        try:
            # Extract date and time from post_data
            post_date = post_data["start_date"]
            post_time = post_data["start_time"]

            # Parse date and time strings
            if isinstance(post_date, str):
                post_date = datetime.strptime(post_date, "%Y-%m-%d").date()
            if isinstance(post_time, str):
                post_time = datetime.strptime(post_time, "%H:%M:%S").time()

            # Combine date and time into a single datetime object
            scheduled_datetime = datetime.combine(post_date, post_time)

            # Get the current datetime
            now = datetime.now()

            # Return True if the post is scheduled for now or later
            return scheduled_datetime <= now

        except Exception as e:
            print(f"Error while checking if post is due: {e}")
            return False

    @staticmethod
    async def get_all_scheduled_posts(
        db: AsyncIOMotorDatabase,
    ) -> List[SocialMediaPost]:
        query = {"status": PostStatusEnum.SCHEDULED}
        cursor = db["social_media_posts"].find(query)
        scheduled_posts_list = await cursor.to_list(length=1000)
        scheduled_posts_list = [
            SocialMediaPost(**post).dict() for post in scheduled_posts_list
        ]
        return scheduled_posts_list

    @staticmethod
    async def post_scheduled_post(
        db: AsyncIOMotorDatabase, post_data: dict, platform: str
    ):
        try:
            print("Getting influencer data...")
            data = await InfluencerRepository.get_influencer_by_social_user_id(
                db, social_user_id=post_data.get("social_user_id", None)
            )
            print("Influencer data found...", data)

            if not data:
                raise ValueError(
                    f"Influencer data not found for {post_data.get('social_user_id', None)}"
                )

            influencer_data = data.get("responseData", {})

            print("Influencer data from response...", influencer_data)
            access_token = influencer_data.get("token", "")
            if not access_token:
                raise ValueError(f"Access token for {platform} not found")
            if platform == "TWITTER":
                response = await SocialMediaPostService.post_on_twitter(
                    post_data=post_data, x_access_token=access_token
                )
            elif platform == "LINKEDIN":
                response = await SocialMediaPostService.post_on_linkedin(
                    post_data=post_data, influencer_data=influencer_data
                )
            elif platform == "TIKTOK":
                response = await SocialMediaPostService.post_on_tiktok(
                    post_data=post_data, influencer_data=influencer_data
                )
            elif platform == "FACEBOOK":
                response = await SocialMediaPostService.post_on_facebook(
                    post_data=post_data, influencer_data=influencer_data
                )
            elif platform == "INSTAGRAM":
                response = await SocialMediaPostService.post_on_instagram(
                    post_data=post_data, influencer_data=influencer_data
                )

            print("\nResponse from posting scheduled post: ", response)
            if response.get("status", None):
                await SocialMediaPostRepository.update_post_status(
                    db, post_data["post_id"], PostStatusEnum.PUBLISHED
                )
                print(f"\nScheduled post successful: {post_data}")
            else:
                await SocialMediaPostRepository.update_post_status(
                    db, post_data["post_id"], PostStatusEnum.FAILED
                )
                print(f"\nScheduled post failed: {post_data}")

        except Exception as e:
            await SocialMediaPostRepository.update_post_status(
                db, post_data["post_id"], PostStatusEnum.FAILED
            )
            print(f"\nError posting scheduled post: {e}")

    @staticmethod
    async def post_on_twitter(post_data: dict, x_access_token: str = "access_token"):
        payload = TwitterHelper.create_twitter_post_payload_from_post_dict(post_data)
        await XManageTweetService.create_tweet(
            access_token=x_access_token, payload=payload.dict()
        )
        post_data["post_type"] = PostStatusEnum.PUBLISHED

    @staticmethod
    async def post_on_linkedin(post_data: dict, influencer_data: dict):
        token_data = influencer_data.get("token", {})
        if type(token_data) is str:
            linkedin_access_token = token_data
        else:
            linkedin_access_token = token_data.get(
                LinkedInTokenScopeEnum.CONTENT_MANAGEMENT.value, None
            )
        account_type = influencer_data["account_type"]
        try:
            if len(post_data["media"]) > 0:
                payload = LinkedinHelper.create_linkedin_media_post_payload_from_dict(
                    post_data, account_type=account_type
                )
                response = await LinkedInManageShareService.create_media_share_content(
                    payload, linkedin_access_token
                )
            elif post_data["post_url"]:
                payload = LinkedinHelper.create_linkedin_article_post_payload_from_dict(
                    post_data, account_type=account_type
                )
                response = (
                    await LinkedInManageShareService.create_share_article_content(
                        payload, linkedin_access_token
                    )
                )
            else:
                payload = LinkedinHelper.create_linkedin_text_post_payload_from_dict(
                    post_data, account_type=account_type
                )
                response = await LinkedInManageShareService.create_share_text_content(
                    payload, linkedin_access_token
                )
            print("\nResponse from posting on LinkedIn: ", response)
            return response
        except Exception as e:
            print("Exception when posting on LinkedIn: ", e)

    @staticmethod
    async def post_on_instagram(post_data: dict, influencer_data: dict):
        payload = InstagramHelper.construct_post_media_request(post_data)
        response = await InstagramService.publish_media_post(
            influencer_data["social_user_id"], payload, influencer_data["token"]
        )
        return response

    @staticmethod
    async def post_on_facebook(post_data: dict, influencer_data: dict):
        if influencer_data:
            print("found page data", influencer_data)
            print("found post data", post_data)
            page_id = influencer_data.get("social_user_id", "")
            try:
                print("constructing payload....", post_data)
                if post_data["post_type"] == PostTypeEnum.POST:
                    response = await FacebookService.post_on_facebook(
                        page_id, post_data, influencer_data.get("token", "")
                    )
                elif post_data["post_type"] == PostTypeEnum.REEL:
                    response = await FacebookService.publish_reel_video(
                        page_id, post_data, influencer_data.get("token", "")
                    )
                print("done....", response)
                print("Facebook response: ", response)
                return response
            except Exception as e:
                print("\nError posting facebook scheduled post: ", e)
                raise e

    @staticmethod
    async def schedule_facebook_post(
        db: AsyncIOMotorDatabase, post_data: dict, access_token: str
    ):
        if post_data["post_type"] == PostTypeEnum.POST:
            payload = FacebookHelper.construct_scheduled_post_payload_from_dict(
                post_data
            )
            response = await FacebookService.publish_post(
                post_data["settings"]["page_id"], payload, access_token
            )
        if response.get("status", None):
            await SocialMediaPostRepository.update_post_status(
                db, post_data["post_id"], PostStatusEnum.QUEUED
            )

    @staticmethod
    async def post_on_tiktok(post_data: dict, influencer_data: dict):
        payload = TiktokHelper.construct_payload_from_dict(post_data)
        tiktok_access_token = influencer_data.get("token", "")
        response = await TiktokService.initiate_media_upload(
            tiktok_access_token, payload
        )
        return response
