from fastapi import APIRouter, Depends, Query
from app.domain.responses.uri_response import UriResponse
from app.services.RedditService import RedditService
from app.domain.requests.reddit_requests import (
    RedditCommentsSearchParams,
    RedditSearchParams,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency

router = APIRouter()


@router.get("/comments/search")
async def search_all_comments(
    params: RedditCommentsSearchParams = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Perform a most recent comments search for posts using the Reddit API.

    The request body must include all the necessary parameters as defined in the RedditSearchParams model.
    """
    response = await RedditService.get_comments(db, 100, params)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/search")
async def search(
    params: RedditSearchParams = Query(None),
):
    response = await RedditService.get_multiple_search_data(params)
    print("\nResponse: ", response)
    return UriResponse.get_single_data_response("reddit search result", response)
