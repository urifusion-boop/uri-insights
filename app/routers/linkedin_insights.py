from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from app.domain.enums.linkedin_enum import (
    LinkedInReactionTypeEnum,
    LinkedInTokenScopeEnum,
)
from app.services.LinkedInAnalyticService import LinkedInAnalyticService
from app.services.LinkedInConversionService import LinkedInConversionService
from app.services.LinkedInCommunityMgtService import LinkedInCommunityMgtService
from app.services.LinkedInService import LinkedInService
from app.domain.requests.linkedin_requests import *
from app.domain.responses.uri_response import UriResponse
from app.dependencies import (
    enforce_feature_limit,
    get_db_dependency,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from typing import Optional
from datetime import datetime
from app.core.auth_handler import get_linkedin_access_token


router = APIRouter()


@router.get("/linkedin/business-discovery")
async def get_linkedin_discovery(
    organization_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.fetch_business_discovery(
        access_token=access_token,
        db=db,
        organization_id=organization_id,
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/advertising/insights")
async def get_linkedin_ad_insights(
    bearer_token: str,
    pivot: str,
    campaign_id: str,
    time_granularity: str,
    start_date: str,  # Format: 22-04-2024
    end_date: str,
):
    if start_date:
        date_obj = datetime.strptime(start_date, "%d-%m-%Y")
        start_date_dict = {
            "year": date_obj.year,
            "month": date_obj.month,
            "day": date_obj.day,
        }

    if end_date:
        date_obj = datetime.strptime(end_date, "%d-%m-%Y")
        end_date_dict = {
            "year": date_obj.year,
            "month": date_obj.month,
            "day": date_obj.day,
        }

    response = await LinkedInAnalyticService.fetch_analytics(
        bearer_token=bearer_token,
        pivot=pivot,
        campaign_id=campaign_id,
        time_granularity=time_granularity,
        start_date=start_date_dict,
        end_date=end_date_dict,
    )
    print(response)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/linkedin/conversions/create")
async def create_conversion_rule(request: CreateConversionRuleRequest):
    response = await LinkedInConversionService.create_conversion_rule(request)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/conversions/fetch")
async def fetch_conversion_rules(ad_account_id: str, bearer_token: str):
    response = await LinkedInConversionService.fetch_conversion_rules(
        ad_account_id=ad_account_id, bearer_token=bearer_token
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/linkedin/conversions/stream-event")
async def stream_conversion_event(request: StreamConversionEventRequest):
    response = await LinkedInConversionService.stream_conversion_events(request)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/oganisation/vanityname")
async def find_organization_by_vanity_name(
    vanity_name: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.find_organization_by_vanity_name(
        db, vanity_name, access_token
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/linkedin/community/share/company-mention")
async def create_share_with_company_mention(
    payload: SharePayload,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.create_share_with_company_mention(
        db, payload, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/linkedin/community/subscription/create")
async def create_subscription_request(
    payload: SubscriptionPayload,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.create_subscription_request(
        db, payload, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/notifications")
async def retrieve_notifications(
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.retrieve_notifications(
        db, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.delete("/linkedin/community/subscription/remove")
async def remove_subscription(
    subscription_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.remove_subscription(
        db, subscription_id, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/follower/statistics")
async def retrieve_lifetime_follower_statistics(
    organization_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.retrieve_lifetime_follower_statistics(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/follower/statistics/time-bound")
async def retrieve_time_bound_follower_statistics(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    params: TimeBoundStatistics = Query(None),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = (
        await LinkedInCommunityMgtService.retrieve_time_bound_follower_statistics(
            db=db,
            organization_id=params.organization_id,
            date_range=params.date_range,
            time_granularity=params.time_granularity,
            access_token=access_token,
        )
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/share/statistics/time-bound")
async def retrieve_time_bound_share_statistics(
    params: TimeBoundStatistics = Query(None),
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.retrieve_time_bound_share_statistics(
        organization_id=params.organization_id,
        date_range=params.date_range,
        time_granularity=params.time_granularity,
        access_token=access_token,
        db=db,
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/share/statistics/life-time")
async def retrieve_life_time_share_statistics(
    organization_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.retrieve_life_time_share_statistics(
        organization_id=organization_id, access_token=access_token, db=db
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/share/statistics/specific-share")
async def retrieve_life_time_share_statistics_for_specific_shares(
    organization_id: str,
    share_ids: str = Query(
        None, description=("Comma-separated list of share ids to retrieve.")
    ),
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.retrieve_life_time_statistics_for_specific_shares(
        organization_id=organization_id,
        share_ids=share_ids,
        access_token=access_token,
        db=db,
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/ugcposts/statistics/specific-ugcpost")
async def retrieve_life_time_share_statistics_for_specific_ugc_posts(
    organization_id: str,
    ugc_posts_ids: str = Query(
        None, description=("Comma-separated list of UGC posts ids to retrieve.")
    ),
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.retrieve_life_time_statistics_for_specific_ugc_posts(
        organization_id=organization_id,
        ugc_post_ids=ugc_posts_ids,
        access_token=access_token,
        db=db,
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/search/keyword")
async def search_by_keyword(
    organization_id: str,
    keyword: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.search_by_keyword(
        db, organization_id, keyword, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/organization/followers/count")
async def retrieve_organization_follower_count(
    organization_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.retrieve_organization_follower_count(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/organization/email-domain")
async def find_organization_by_email_domain(
    email_domain: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.find_organization_by_email_domain(
        db, email_domain, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/organization/{organization_id}")
async def retrieve_organization_by_id(
    organization_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.retrieve_organization_by_id(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/organization/projection/{organization_id}")
async def retrieve_organization_using_projection(
    organization_id: str,
    projection: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.retrieve_organization_using_projection(
        db, organization_id, projection, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/linkedin/community/organization/non-administered")
async def find_non_administered_organization(
    organization_ids: List[str],
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.find_non_administered_organization(
        db, organization_ids, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/organization/primary-type/{organization_id}")
async def lookup_by_organization_primary_type(
    organization_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.lookup_by_organization_primary_type(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/organization/admin-brands/{organization_brand_id}")
async def retrieve_administered_organization_brand(
    organization_brand_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = (
        await LinkedInCommunityMgtService.retrieve_administered_organization_brand(
            db, organization_brand_id, access_token
        )
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/linkedin/community/organization/brands/admin")
async def batch_get_on_administered_organization_brands(
    organization_brand_ids: List[str],
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = (
        await LinkedInCommunityMgtService.batch_get_on_administered_organization_brands(
            db, organization_brand_ids, access_token
        )
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/linkedin/community/organization/brands/non-admin")
async def batch_get_on_non_administered_organization_brands(
    organization_brand_ids: List[str],
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.batch_get_on_non_administered_organization_brands(
        db, organization_brand_ids, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/linkedin/community/organization/admin-brands/parent/{parent_organization_id}"
)
async def find_administered_organization_brands_by_parent_org(
    parent_organization_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.find_administered_organization_brands_by_parent_org(
        db, parent_organization_id, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/organization/access-control")
async def find_member_organization_access_control(
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = (
        await LinkedInCommunityMgtService.find_member_organization_access_control(
            db, access_token
        )
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/organization/{organization_id}/administrators")
async def find_organization_administrators(
    organization_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.find_organization_administrators(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/community/organization/{organization_id}/access-control")
async def find_organization_access_control(
    organization_id: str,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.find_organization_access_control(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/save-linkedin-account")
async def save_linkedin_account(
    user_id: str,
    token_scope: LinkedInTokenScopeEnum,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    max_accounts=Depends(enforce_feature_limit),
):
    if (
        max_accounts
        and isinstance(max_accounts, dict)
        and max_accounts.get("responseCode") == 400
    ):
        return UriResponse.get_status_response(
            response=max_accounts, status_code=max_accounts.get("responseCode", "")
        )
    data = await LinkedInService.save_linkedin_account(
        user_id=user_id,
        access_token=access_token,
        token_scope=token_scope,
        db=db,
        max_accounts=max_accounts,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/posts",
    summary="Get linkedin posts",
    description="Get all posts for a linkedin organization.",
)
async def get_posts(
    organization_id: str,
    start: int = 0,
    count: int = 10,
    sort_by: LinkedInPostRetrievalOrderEnum = LinkedInPostRetrievalOrderEnum.CREATED,
    access_token: str = Depends(get_linkedin_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await LinkedInCommunityMgtService.get_organization_posts(
        organization_id=organization_id,
        access_token=access_token,
        db=db,
        start=start,
        count=count,
        sort_by=sort_by,
    )

    return UriResponse.get_status_response(response=response)


@router.get(
    "/posts/comments",
    summary="Get linkedin comments",
    description="Get all posts for a linkedin share.",
)
async def get_share_comments(
    share_id: str,
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.get_comments_for_a_share(
        share_id=share_id,
        access_token=access_token,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/posts/engagements",
    summary="Get linkedin engagements",
    description="Get all engagements on a post",
)
async def get_share_engagements(
    share_urn: str,
    sort: Optional[LinkedInReactionTypeEnum] = None,
    start: Optional[int] = None,
    count: Optional[int] = None,
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.get_reactions_for_a_share(
        share_urn=share_urn,
        access_token=access_token,
    )

    return UriResponse.get_status_response(response=response)


@router.get("/ai-media-report")
async def media_ai_reports(
    cache_key: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LinkedInCommunityMgtService.fetch_ai_post_report(db, cache_key)

    return UriResponse.get_status_response(
        response=data, status_code=data["responseCode"]
    )
