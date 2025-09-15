from fastapi import APIRouter, HTTPException, Depends
from http import HTTPStatus
from app.services.LinkedInCampaignService import LinkedInCampaignService
from app.services.LinkedInConversionService import LinkedInConversionService
from app.domain.requests.linkedin_requests import *
from app.domain.responses.uri_response import UriResponse
from app.dependencies import get_db_dependency
from motor.motor_asyncio import AsyncIOMotorDatabase

from pydantic import BaseModel
from typing import Optional


router = APIRouter()


@router.post("/linkedin/campaigns/create")
async def create_linkedin_campaign(request: CreateCampaignRequest):
    response = await LinkedInCampaignService.create_campaign(request)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/campaigns/fetch")
async def fetch_campaign(account_id: str, campaign_id: str, bearer_token: str):
    response = await LinkedInCampaignService.fetch_campaign(
        account_id=account_id, campaign_id=campaign_id, bearer_token=bearer_token
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/campaigns/search")
async def fetch_campaigns(
    account_id: str, campaign_type: str, status: str, sort_order: str, bearer_token: str
):
    response = await LinkedInCampaignService.search_campaigns(
        account_id=account_id,
        campaign_type=campaign_type,
        status=status,
        sort_order=sort_order,
        bearer_token=bearer_token,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/linkedin/campaign-groups/create")
async def create_linkedin_campaign_group(request: CreateCampaignGroupRequest):
    response = await LinkedInCampaignService.create_campaign_group(request)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/campaign-groups/fetch")
async def fetch_campaign_group(account_id: str, campaign_id: str, bearer_token: str):
    response = await LinkedInCampaignService.fetch_campaign_group(
        account_id=account_id, campaign_group_id=campaign_id, bearer_token=bearer_token
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/linkedin/campaign-groups/search")
async def search_campaign_group(
    account_id: str, status: str, sort_order: str, bearer_token: str
):
    response = await LinkedInCampaignService.search_campaign_groups(
        account_id=account_id,
        status=status,
        sort_order=sort_order,
        bearer_token=bearer_token,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/linkedin/campaigns/link-conversion")
async def link_conversion_rule(request: LinkConversionToCampaignRequest):
    response = await LinkedInConversionService.associate_conversion_rule_to_campaign(
        request
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
