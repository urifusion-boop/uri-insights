from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.OpenAIApifyFacebookService import OpenAIApifyFacebookService
from app.domain.responses.uri_response import UriResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class PostAnalysisRequest(BaseModel):
    keyword: str
    max_posts: Optional[int] = 10
    analyze_sentiment: Optional[bool] = True


class PostSummaryRequest(BaseModel):
    keyword: str
    max_posts: Optional[int] = 10


@router.post("/fetch-and-analyze-posts")
async def fetch_and_analyze_posts(request: PostAnalysisRequest):
    try:
        service = OpenAIApifyFacebookService()
        result = await service.fetch_posts_with_analysis(
            keyword=request.keyword,
            max_posts=request.max_posts,
            analyze_sentiment=request.analyze_sentiment,
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error_message", "Unknown error"))

        return UriResponse.get_single_data_response(
            entity_name="Facebook Post Analysis",
            data=result,
            message=f"Successfully fetched and analyzed {result['total_posts']} posts for keyword '{request.keyword}'",
        )
    except Exception as e:
        logger.error(f"Error in fetch_and_analyze_posts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fetch-posts")
async def fetch_posts_simple(
    keyword: str = Query(..., description="Keyword to search for Facebook posts"),
    max_posts: int = Query(2, description="Maximum number of posts to fetch", ge=1, le=50),
    analyze_sentiment: bool = Query(False, description="Whether to analyze sentiment using OpenAI"),
):
    try:
        service = OpenAIApifyFacebookService()
        result = await service.fetch_posts_with_analysis(keyword=keyword, max_posts=max_posts, analyze_sentiment=analyze_sentiment)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error_message", "Unknown error"))

        return UriResponse.get_single_data_response(
            entity_name="Facebook Post Analysis",
            data=result,
            message=f"Successfully fetched and analyzed {result['total_posts']} posts for keyword '{keyword}'",
        )
    except Exception as e:
        logger.error(f"Error in fetch_posts_simple: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-post-summary")
async def generate_post_summary(request: PostSummaryRequest):
    try:
        service = OpenAIApifyFacebookService()
        posts_result = await service.fetch_posts_with_analysis(keyword=request.keyword, max_posts=request.max_posts)
        if not posts_result.get("success"):
            raise HTTPException(status_code=500, detail=posts_result.get("error_message", "Unknown error"))

        summary_result = await service.generate_post_summary(posts_result.get("posts", []))
        if not summary_result.get("success"):
            raise HTTPException(status_code=500, detail=summary_result.get("error_message", "Unknown error"))

        return UriResponse.get_single_data_response(
            entity_name="Facebook Post Summary",
            data={
                "keyword": request.keyword,
                "posts": posts_result.get("posts", []),
                "summary": summary_result,
                "total_posts": posts_result.get("total_posts", 0),
            },
            message=f"Successfully generated summary for {posts_result.get('total_posts', 0)} posts about '{request.keyword}'",
        )
    except Exception as e:
        logger.error(f"Error in generate_post_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    return UriResponse.get_single_data_response(
        entity_name="OpenAI Apify Facebook Integration",
        data={"service": "OpenAI Apify Facebook Integration", "status": "healthy"},
        message="Service is running",
    )