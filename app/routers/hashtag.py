from fastapi import APIRouter, BackgroundTasks, Query, Depends
from app.domain.responses.uri_response import UriResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency
from app.domain.responses.uri_response import UriResponse
from app.services.HashtagService import HashtagService

router = APIRouter()


@router.get("/track")
async def track_hashtag(
    background_tasks: BackgroundTasks,
    hashtag: str = Query(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    meta_access_token: str = Query(None),
):
    """
    Perform a recent search for hashtag using multiple API.
    """
    response = await HashtagService.search(
        hashtag, db, background_tasks, meta_access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/ai_post_report")
async def get_ai_post_report(
    hashtag_cache_key: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Perform ai report for hashtag result.

    """
    response = await HashtagService.fetch_post_report(db, hashtag_cache_key)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/sentiment_analysis")
async def get_sentiment_analysis(
    hashtag_cache_key: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await HashtagService.fetch_sentiment_analysis(db, hashtag_cache_key)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/ai_hashtag_report")
async def get_ai_hashtag_report(
    hashtag: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Perform ai insight report for hashtag posts.

    """
    response = await HashtagService.analyze_hashtag_conversations(db, hashtag)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
