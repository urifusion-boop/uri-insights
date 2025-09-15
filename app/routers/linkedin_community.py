from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Body
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums.linkedin_enum import LinkedInTimeGranularityEnum
from app.services.LinkedInAnalyticService import LinkedInAnalyticService
from app.services.LinkedInCommunityMgtService import LinkedInCommunityMgtService
from app.domain.requests.linkedin_requests import (
    SharePayload,
    SubscriptionPayload,
    TimeBoundStatistics,
)
from app.dependencies import get_db_dependency
from app.domain.responses.uri_response import UriResponse
from app.core.auth_handler import get_linkedin_access_token

router = APIRouter()


@router.post(
    "/shares",
    summary="Create a Share with Company Mention",
    description="Create a LinkedIn share with a company mention.",
)
async def create_share(
    payload: SharePayload = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.create_share_with_company_mention(
        db, payload, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.put(
    "/subscriptions",
    summary="Create a Subscription Request",
    description="Create a subscription request for organization social action notifications.",
)
async def create_subscription(
    payload: SubscriptionPayload = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.create_subscription_request(
        db, payload, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/notifications",
    summary="Retrieve Notifications",
    description="Retrieve notifications for the authenticated member's organization.",
)
async def get_notifications(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.retrieve_notifications(
        db, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.delete(
    "/subscriptions/{subscription_id}",
    summary="Remove Subscription",
    description="Remove a subscription for organization social action notifications.",
)
async def remove_subscription(
    subscription_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.remove_subscription(
        db, subscription_id, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/notifications",
    summary="Retrieve Notifications",
    description="Retrieve notifications for the authenticated member's organization.",
)
async def retrieve_notifications(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.retrieve_notifications(
        db, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/follower-statistics/lifetime",
    summary="Retrieve Lifetime Follower Statistics",
    description="Retrieve lifetime follower statistics for an organization.",
)
async def retrieve_lifetime_follower_statistics(
    organization_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.retrieve_lifetime_follower_statistics(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/follower-statistics/time-bound",
    summary="Retrieve Time-Bound Follower Statistics",
    description="Retrieve time-bound follower statistics for an organization.",
)
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
    return UriResponse.get_status_response(response=response)


@router.get(
    "/share-statistics/time-bound",
    summary="Retrieve Time-Bound Share Statistics",
    description="Retrieve time-bound share statistics for an organization.",
)
async def retrieve_time_bound_share_statistics(
    params: TimeBoundStatistics = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.retrieve_time_bound_share_statistics(
        db=db,
        organization_id=params.organization_id,
        date_range=params.date_range,
        time_granularity=params.time_granularity,
        access_token=access_token,
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/search/keyword",
    summary="Search by Keyword",
    description="Search for people in an organization by keyword.",
)
async def search_by_keyword(
    organization_id: str = Query(...),
    keyword: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.search_by_keyword(
        db, organization_id, keyword, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/search/vanity-url",
    summary="Search by Vanity URL",
    description="Search for an organization by its vanity URL.",
)
async def search_by_vanity_url(
    organization_id: str = Query(...),
    vanity_url: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.search_by_vanity_url(
        db, organization_id, vanity_url, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization/{organization_id}",
    summary="Retrieve Organization by ID",
    description="Retrieve details of an organization by its ID.",
)
async def retrieve_organization_by_id(
    organization_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.retrieve_organization_by_id(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization/{organization_id}/follower-count",
    summary="Retrieve Organization Follower Count",
    description="Retrieve the follower count of an organization.",
)
async def retrieve_organization_follower_count(
    organization_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.retrieve_organization_follower_count(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization/{organization_id}/projection",
    summary="Retrieve Organization Using Projection",
    description="Retrieve an organization using a projection.",
)
async def retrieve_organization_using_projection(
    organization_id: str,
    projection: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.retrieve_organization_using_projection(
        db, organization_id, projection, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization/non-administered",
    summary="Find Non-Administered Organizations",
    description="Find non-administered organizations by IDs.",
)
async def find_non_administered_organization(
    organization_ids: List[str] = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.find_non_administered_organization(
        db, organization_ids, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization/{organization_id}/primary-type",
    summary="Lookup by Organization Primary Type",
    description="Retrieve the primary type of an organization.",
)
async def lookup_by_organization_primary_type(
    organization_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.lookup_by_organization_primary_type(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization/search/vanity-name",
    summary="Find Organization by Vanity Name",
    description="Find an organization using its vanity name.",
)
async def find_organization_by_vanity_name(
    vanity_name: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.find_organization_by_vanity_name(
        db, vanity_name, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization/batch",
    summary="Batch GET by Administered Org IDs",
    description="Retrieve details for multiple administered organizations by their IDs.",
)
async def batch_get_by_administered_org_ids(
    organization_ids: List[str] = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.batch_get_by_administered_org_ids(
        db, organization_ids, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization/brands/search",
    summary="Find Organization Brand by Vanity Name",
    description="Find an organization brand using its vanity name.",
)
async def find_organization_brand_by_vanity_name(
    vanity_name: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.find_organization_brand_by_vanity_name(
        db, vanity_name, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization/brands/{organization_brand_id}",
    summary="Retrieve Administered Organization Brand",
    description="Retrieve an administered organization brand by its ID.",
)
async def retrieve_administered_organization_brand(
    organization_brand_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = (
        await LinkedInCommunityMgtService.retrieve_administered_organization_brand(
            db, organization_brand_id, access_token
        )
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization-brands/administered/batch",
    summary="Batch GET on Administered Organization Brands",
    description="Retrieve details for multiple administered organization brands by their IDs.",
)
async def batch_get_on_administered_organization_brands(
    organization_brand_ids: List[str] = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = (
        await LinkedInCommunityMgtService.batch_get_on_administered_organization_brands(
            db, organization_brand_ids, access_token
        )
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization-brands/non-administered/batch",
    summary="Batch GET on Non-Administered Organization Brands",
    description="Retrieve details for multiple non-administered organization brands by their IDs.",
)
async def batch_get_on_non_administered_organization_brands(
    organization_brand_ids: List[str] = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.batch_get_on_non_administered_organization_brands(
        db, organization_brand_ids, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization-brands/by-parent",
    summary="Find Administered Organization Brands by Parent Organization",
    description="Find administered organization brands using the parent organization ID.",
)
async def find_administered_organization_brands_by_parent_org(
    parent_organization_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.find_administered_organization_brands_by_parent_org(
        db, parent_organization_id, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization-acls/role-assignee",
    summary="Find Member's Organization Access Control",
    description="Find a member's organization access control.",
)
async def find_member_organization_access_control(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = (
        await LinkedInCommunityMgtService.find_member_organization_access_control(
            db, access_token
        )
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization-acls/{organization_id}/administrators",
    summary="Find Organization Administrators",
    description="Find administrators of an organization.",
)
async def find_organization_administrators(
    organization_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.find_organization_administrators(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/organization-acls/{organization_id}/access-control",
    summary="Find Organization Access Control",
    description="Find access control details for an organization.",
)
async def find_organization_access_control(
    organization_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInCommunityMgtService.find_organization_access_control(
        db, organization_id, access_token
    )
    return UriResponse.get_status_response(response=response)
