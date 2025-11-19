from fastapi import APIRouter, HTTPException, Query
from app.services.OpenAIApifyTiktokService import OpenAIApifyTiktokService
from app.domain.responses.uri_response import UriResponse

router = APIRouter()

@router.get("/fetch-posts")
async def fetch_posts(keyword: str = Query(...), max_posts: int = Query(2, ge=1, le=50), analyze_sentiment: bool = Query(False)):
    try:
        service = OpenAIApifyTiktokService()
        result = await service.fetch_posts_with_analysis(keyword=keyword, max_posts=max_posts, analyze_sentiment=analyze_sentiment)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error_message", "Unknown error"))
        return UriResponse.get_single_data_response(
            entity_name="TikTok Posts",
            data=result,
            message=f"Fetched {result.get('total_posts', 0)} TikTok posts for '{keyword}'"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return UriResponse.get_single_data_response(
        entity_name="OpenAI Apify TikTok Integration",
        data={"service": "OpenAI Apify TikTok Integration", "status": "healthy"},
        message="Service is running"
    )