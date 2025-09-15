from fastapi import APIRouter
from app.services.SentimentService import SentimentService
from app.domain.requests.linkedin_requests import *
from app.domain.responses.uri_response import UriResponse
from fastapi import APIRouter
from app.services.GoogleService import GoogleService
from app.domain.responses.uri_response import UriResponse
from app.domain.requests.instagram_requests import (
    CommentSentimentRequest,
)

router = APIRouter()


@router.get("/analysis")
async def analyze_sentiment(text: str):
    response = await SentimentService.analyze_sentiment(text)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/comment-sentiment")
async def instagram_business_media_comment_sentiment(request: CommentSentimentRequest):
    data = await GoogleService.analyze_comments_sentiment(request.comments, "caption")

    response = UriResponse.get_single_data_response("comment sentiment", data)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
