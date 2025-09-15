from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from app.services.TiktokService import TiktokService
from app.domain.responses.uri_response import UriResponse
from app.dependencies import get_db_dependency
from motor.motor_asyncio import AsyncIOMotorDatabase

from pydantic import BaseModel
from typing import Optional, List
from app.core.auth_handler import get_tiktok_access_token
from fastapi.encoders import jsonable_encoder
from app.domain.requests.tiktok_requests import PostModel
from fastapi.encoders import jsonable_encoder

router = APIRouter()


@router.get("/hashtag-search")
async def search_tiktok_hashtag(
    hashtag: List[str],
    fields: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None),
):
    response = await TiktokService.fetch_hashtag_search(
        keyword=hashtag,
        fields=fields,
        start_date=start_date,
        end_date=end_date,
        cursor=cursor,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/business-discovery")
async def tiktok_business_discovery(
    username: str,
    fields: Optional[
        str
    ] = "username,display_name,open_id,union_id,avatar_url_100,avatar_url,avatar_large_url,profile_deep_link,is_verified,bio_description,is_verified,follower_count,following_count,likes_count,video_count",
    tiktok_access_token: str = Depends(get_tiktok_access_token),
):
    response = await TiktokService.fetch_business_discovery(
        username, tiktok_access_token, fields=fields
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/media")
async def fetch_business_media(
    fields: Optional[
        str
    ] = "id,title,video_description,duration,cover_image_url,embed_link",
    next: Optional[str] = None,
    tiktok_access_token: str = Depends(get_tiktok_access_token),
):
    response = await TiktokService.fetch_business_media(
        tiktok_access_token, fields, next
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/save-tiktok-account")
async def save_tiktok_account(
    user_id: str,
    username: str,
    tiktok_access_token: str = Depends(get_tiktok_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await TiktokService.save_tiktok_account(
        user_id, username, tiktok_access_token, db
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/video-stats")
async def get_video_stats(
    video_ids: List[str] = Query(...),
    tiktok_access_token: str = Depends(get_tiktok_access_token),
):
    response = await TiktokService.fetch_video_stats(
        access_token=tiktok_access_token, video_ids=video_ids
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/user-demographics")
async def get_user_demographics(
    username: str,
    tiktok_access_token: str = Depends(get_tiktok_access_token),
):
    response = await TiktokService.fetch_user_demographics(
        access_token=tiktok_access_token, username=username
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/video-impressions-reach")
async def get_video_impressions_and_reach(
    video_ids: List[str] = Query(...),
    tiktok_access_token: str = Depends(get_tiktok_access_token),
):
    response = await TiktokService.fetch_video_impressions_and_reach(
        access_token=tiktok_access_token, video_ids=video_ids
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/video-comments")
async def get_video_comments(
    video_id: str,
    tiktok_access_token: str = Depends(get_tiktok_access_token),
):
    response = await TiktokService.fetch_video_comments(
        access_token=tiktok_access_token, video_id=video_id
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/media-upload")
async def initiate_media_upload(
    post_model: PostModel,
    tiktok_access_token: str = Depends(get_tiktok_access_token),
):
    """
    Initiates a media upload (video or photo) to TikTok.
    """
    response = await TiktokService.initiate_media_upload(
        access_token=tiktok_access_token,
        post_model=post_model,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/video-upload-file")
async def upload_video_file(
    upload_url: str,
    file: UploadFile = File(...),
):
    """
    Uploads a video file to TikTok using the provided upload URL.
    """
    try:
        file_location = f"/tmp/{file.filename}"
        with open(file_location, "wb") as buffer:
            buffer.write(file.file.read())

        response = await TiktokService.upload_video_from_file(
            upload_url=upload_url,
            video_path=file_location,
        )
        return UriResponse.get_status_response(
            response=response, status_code=response["responseCode"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video upload failed: {str(e)}")


@router.get("/post-status")
async def fetch_post_status(
    publish_id: str,
    tiktok_access_token: str = Depends(get_tiktok_access_token),
):
    """
    Fetches the status of a media post using the publish ID.
    """
    response = await TiktokService.fetch_post_status(
        access_token=tiktok_access_token,
        publish_id=publish_id,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
