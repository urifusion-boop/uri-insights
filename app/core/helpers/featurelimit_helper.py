from typing import List, Optional
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums.endpoints_enum import EndpointsEnum
from app.repository.InfluencerRepository import InfluencerRepository
from app.repository.TrackerRepository import TrackerRepository


class FeatureLimitHelper:
    endpoint_to_feature_name_map = {
        EndpointsEnum.SAVE_LINKEDIN_ACCOUNTS.value: "linkedinAccounts",
        EndpointsEnum.SAVE_INSTAGRAM_ACCOUNTS.value: "instagramAccounts",
        EndpointsEnum.SAVE_FACEBOOK_ACCOUNTS.value: "facebookAccounts",
        EndpointsEnum.HASHTAG_TRACKING.value: "hashtag",
        EndpointsEnum.KEYWORD_TRACKIING.value: "keyword",
        EndpointsEnum.REPORT_GEN.value: "reportGeneration",
        EndpointsEnum.INSIGHTS_ASSISTANT.value: "aiMessage",
        EndpointsEnum.CREATE_INFLUENCER.value: "instagramAccounts",
        EndpointsEnum.SET_LEADS_AI_REPLY_CONTEXT.value: "lead",
        EndpointsEnum.LEAD_ENRICHMENT.value: "lead",
        EndpointsEnum.LEAD_ENRICHMENT_PHONE.value: "lead",
        EndpointsEnum.LEAD_ENRICHMENT_EMAIL.value: "lead",
    }

    account_tracking_sub_features = [
        "linkedinAccounts",
        "instagramAccounts",
        "facebookAccounts",
    ]

    @staticmethod
    async def construct_feature_limit_update_payload(
        db: AsyncIOMotorDatabase, limit_id: str, user_id: str
    ) -> Optional[dict]:
        usage_count_data = await FeatureLimitHelper.get_usage_counts(db, user_id)

        keyword_count = usage_count_data.get("keyword", 0)
        facebook_accounts_count = usage_count_data.get("facebookAccounts", 0)
        linkedin_accounts_count = usage_count_data.get("linkedinAccounts", 0)
        instagram_accounts_count = usage_count_data.get("instagramAccounts", 0)
        hashtag_count = usage_count_data.get("hashtag", 0)

        if sum(usage_count_data.values()) == 0:
            return None

        update_data = {
            "limitId": limit_id,
            "userId": user_id,
            "keyword": {"count": keyword_count},
            "hashtag": {"count": hashtag_count},
            "accountTracking": {
                "accounts": {
                    "count": sum(
                        [
                            facebook_accounts_count,
                            linkedin_accounts_count,
                            instagram_accounts_count,
                        ]
                    )
                },
                "facebookAccounts": {"count": facebook_accounts_count},
                "instagramAccounts": {"count": instagram_accounts_count},
                "linkedinAccounts": {"count": linkedin_accounts_count},
            },
        }

        return update_data

    @staticmethod
    async def get_usage_counts(
        db: AsyncIOMotorDatabase, user_id: str, endpoints: Optional[List[str]] = None
    ) -> dict:
        usage_counts_data = {}
        if not endpoints or (
            endpoints and EndpointsEnum.SAVE_FACEBOOK_ACCOUNTS.value in endpoints
        ):
            facebook_accounts_connected = (
                await InfluencerRepository.get_user_influencer_count_by_filters(
                    db, user_id=user_id, platforms=["FACEBOOK"], connected=True
                )
            )
            usage_counts_data["facebookAccounts"] = facebook_accounts_connected or 0
        if not endpoints or (
            endpoints and EndpointsEnum.SAVE_LINKEDIN_ACCOUNTS.value in endpoints
        ):
            linkedin_accounts_connected = (
                await InfluencerRepository.get_user_influencer_count_by_filters(
                    db, user_id=user_id, platforms=["LINKEDIN"], connected=True
                )
            )
            usage_counts_data["linkedinAccounts"] = linkedin_accounts_connected or 0
        if not endpoints or (
            endpoints and EndpointsEnum.SAVE_INSTAGRAM_ACCOUNTS.value in endpoints
        ):
            instagram_accounts_connected = (
                await InfluencerRepository.get_user_influencer_count_by_filters(
                    db, user_id=user_id, platforms=["INSTAGRAM"], connected=True
                )
            )
            usage_counts_data["instagramAccounts"] = instagram_accounts_connected or 0
        if not endpoints or (
            endpoints and EndpointsEnum.KEYWORD_TRACKIING.value in endpoints
        ):
            # Get current usage on keyword tracking
            tracked_keywords_count = (
                await TrackerRepository.get_trackers_count_by_filter(
                    db, user_id=user_id, tracker_type="KEYWORD"
                )
            )
            usage_counts_data["keyword"] = tracked_keywords_count or 0
        if not endpoints or (
            endpoints and EndpointsEnum.HASHTAG_TRACKING.value in endpoints
        ):
            # Get current usage on hashtag tracking
            tracked_hashtags_count = (
                await TrackerRepository.get_trackers_count_by_filter(
                    db, user_id=user_id, tracker_type="HASHTAG"
                )
            )
            usage_counts_data["hashtag"] = tracked_hashtags_count or 0

        return usage_counts_data

    @staticmethod
    def format_lead_enrichment_url(request: Request) -> Optional[str]:
        query_params = request.query_params

        # Convert to lowercase and check against common truthy values
        reveal_phone = query_params.get("reveal_phone", "").lower() in (
            "true",
            "1",
            "yes",
        )

        if reveal_phone:
            return EndpointsEnum.LEAD_ENRICHMENT_PHONE.value
        return EndpointsEnum.LEAD_ENRICHMENT_EMAIL.value
