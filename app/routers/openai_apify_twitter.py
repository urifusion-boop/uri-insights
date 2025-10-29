from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.OpenAIApifyTwitterService import OpenAIApifyTwitterService
from app.domain.responses.uri_response import UriResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class TweetAnalysisRequest(BaseModel):
    keyword: str
    max_tweets: Optional[int] = 10
    analyze_sentiment: Optional[bool] = True


class TweetSummaryRequest(BaseModel):
    keyword: str
    max_tweets: Optional[int] = 10


@router.post("/fetch-and-analyze-tweets")
async def fetch_and_analyze_tweets(request: TweetAnalysisRequest):
    """
    Fetch tweets using Apify and analyze them with OpenAI.
    
    This endpoint integrates OpenAI with Apify to:
    1. Search for tweets based on a keyword
    2. Fetch tweet data including author information
    3. Analyze sentiment using OpenAI (optional)
    
    Returns tweet data with author information and optional sentiment analysis.
    """
    try:
        service = OpenAIApifyTwitterService()
        
        result = await service.fetch_tweets_with_analysis(
            keyword=request.keyword,
            max_tweets=request.max_tweets,
            analyze_sentiment=request.analyze_sentiment
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error_message", "Unknown error"))
        
        return UriResponse.get_single_data_response(
            entity_name="Tweet Analysis",
            data=result,
            message=f"Successfully fetched and analyzed {result['total_tweets']} tweets for keyword '{request.keyword}'"
        )
        
    except Exception as e:
        logger.error(f"Error in fetch_and_analyze_tweets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fetch-tweets")
async def fetch_tweets_simple(
    keyword: str = Query(..., description="Keyword to search for tweets"),
    max_tweets: int = Query(2, description="Maximum number of tweets to fetch", ge=1, le=50),
    analyze_sentiment: bool = Query(False, description="Whether to analyze sentiment using OpenAI")
):
    """
    Simple GET endpoint to fetch and analyze tweets.
    
    Query Parameters:
    - keyword: The search term for tweets
    - max_tweets: Number of tweets to fetch (1-50)
    - analyze_sentiment: Whether to include OpenAI sentiment analysis
    
    Returns tweet data with author information and optional sentiment analysis.
    """
    try:
        service = OpenAIApifyTwitterService()
        
        result = await service.fetch_tweets_with_analysis(
            keyword=keyword,
            max_tweets=max_tweets
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error_message", "Unknown error"))
        
        return UriResponse.get_single_data_response(
            entity_name="Tweet Analysis",
            data=result,
            message=f"Successfully fetched and analyzed {result['total_tweets']} tweets for keyword '{keyword}'"
        )
        
    except Exception as e:
        logger.error(f"Error in fetch_tweets_simple: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-tweet-summary")
async def generate_tweet_summary(request: TweetSummaryRequest):
    """
    Fetch tweets and generate an AI-powered summary.
    
    This endpoint:
    1. Fetches tweets for the given keyword
    2. Uses OpenAI to generate a comprehensive summary of the tweets
    
    Returns both the individual tweets and an AI-generated summary.
    """
    try:
        service = OpenAIApifyTwitterService()
        
        # First fetch the tweets
        tweets_result = await service.fetch_tweets_with_analysis(
            keyword=request.keyword,
            max_tweets=request.max_tweets
        )
        
        if not tweets_result["success"]:
            raise HTTPException(status_code=500, detail=tweets_result.get("error_message", "Unknown error"))
        
        # Generate summary
        summary_result = await service.generate_tweet_summary(tweets_result["tweets"])
        
        return UriResponse.get_single_data_response(
            entity_name="Tweet Summary",
            data={
                "keyword": request.keyword,
                "tweets": tweets_result["tweets"],
                "summary": summary_result,
                "total_tweets": tweets_result["total_tweets"]
            },
            message=f"Successfully generated summary for {tweets_result['total_tweets']} tweets about '{request.keyword}'"
        )
        
    except Exception as e:
        logger.error(f"Error in generate_tweet_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint for the OpenAI + Apify Twitter service.
    """
    return UriResponse.get_single_data_response(
        entity_name="OpenAI Apify Twitter Integration",
        data={"service": "OpenAI Apify Twitter Integration", "status": "healthy"},
        message="Service is running"
    )