from typing import List
from fastapi import APIRouter, Depends, Query, Body
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.requests.linkedin_requests import (
    GetSharePayload,
    ShareArticleContentPayload,
    ShareMediaContentPayload,
    ShareTextContentPayload,
)
from app.dependencies import get_db_dependency
from app.domain.responses.uri_response import UriResponse
from app.core.auth_handler import get_linkedin_access_token
from app.services.LinkedInManageShareService import LinkedInManageShareService

router = APIRouter()


@router.post(
    "/text-share/create",
    summary="Create a text Share",
    description="Create a LinkedIn text share",
)
async def create_text_share(
    payload: ShareTextContentPayload = Body(...),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInManageShareService.create_share_text_content(
        payload, access_token
    )
    print("Response from linkedin shares", response)
    return UriResponse.get_status_response(response=response)


@router.post(
    "/article-share/create",
    summary="Create an article share",
    description="Create a LinkedIn article share",
)
async def create_article_share(
    payload: ShareArticleContentPayload = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInManageShareService.create_share_article_content(
        payload, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.post(
    "/media-share/create",
    summary="Create a media share",
    description="Create a LinkedIn media with image or video share",
)
async def create_media_share(
    payload: ShareMediaContentPayload = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInManageShareService.create_media_share_content(
        payload, access_token
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/getById",
    summary="Get a media share",
    description="Get a LinkedIn media share by ID",
)
async def get_media_share(
    share_id: str = Query(...),
    access_token: str = Depends(get_linkedin_access_token),
):
    response = await LinkedInManageShareService.get_share_by_id(share_id, access_token)
    return UriResponse.get_status_response(response=response)
