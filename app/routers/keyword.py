from typing import Any, List, Optional
from fastapi import APIRouter, Query, Body, Depends
from app.services.KeywordService import KeywordService
from app.domain.responses.uri_response import UriResponse
from app.domain.requests.google_requests import GoogleSearchParams
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency
from app.services.XTweetSearchService import XTweetSearchService
from app.domain.responses.uri_response import UriResponse
from app.domain.requests.twitter_requests import (
    TweetSearchParams,
)

router = APIRouter()


@router.get(
    "/web/track",
    summary="Track Keyword Insights",
    description=(
        "This endpoint allows users to retrieve keyword insights from Google Custom Search. "
        "It supports a range of parameters for customizing the search query, including filters for keywords, "
        "phrases, languages, locations, and other advanced settings. Results can be paginated and "
        "further refined based on content type, usage rights, and image attributes."
    ),
    response_description="Returns keyword insights based on provided search parameters.",
)
async def track_keyword(
    params: GoogleSearchParams = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Track Keyword Insights

    This endpoint allows users to query Google Custom Search for keyword insights with advanced filters.
    Provides keyword tracking functionality with customizable parameters.

    **Parameters**:
    - `includes`: List of keywords to include in the search query.
    - `excludes`: List of keywords to exclude from the search results.
    - **`phrases`**: List of exact phrases to include in the search, each phrase enclosed in double quotes.
    - **`locations`**: Domains or sites to restrict search results (e.g., 'site:example.com').
    - **`languages`**: Languages to restrict search results (e.g., 'lang_en' for English).
    - **`platforms`**: Specific sites or platforms to prioritize in the search query.
    - **`start_index`**: The starting index for pagination, typically a multiple of count (e.g., 1, 11, 21).
    - **`count`**: Number of results per page (between 1 and 10).
    - **`lr`**: Restricts results to documents in a specified language (e.g., 'lang_en' for English).
    - **`safe`**: Enables or disables safe search filtering ('active' or 'off').
    - **`cx`**: The Custom Search Engine ID to use for the request.
    - **`sort`**: The order of the search results (e.g., 'date' for most recent).
    - **`filter`**: Duplicate content filtering (1 to enable, 0 to disable).
    - **`gl`**: Geolocation country code to fine-tune results based on a location (e.g., 'US' for United States).
    - **`cr`**: Restricts search results to a specific country (e.g., 'countryUS' for United States).
    - **`googlehost`**: Specifies the Google domain to use (e.g., 'google.com' or 'google.co.uk').
    - **`c2coff`**: Disables translation between Simplified and Traditional Chinese ('1' to disable).
    - **`hq`**: Additional query terms to emphasize in the search.
    - **`hl`**: Interface language for the Google search engine (e.g., 'en' for English).
    - **`site_search`**: Restricts search results to a specific site (e.g., 'example.com').
    - **`site_search_filter`**: Site search filtering ('i' includes, 'e' excludes site from results).
    - **`exact_terms`**: Terms that must appear in search results exactly as provided.
    - **`exclude_terms`**: Terms to exclude from search results.
    - **`link_site`**: Restricts results to pages that link to a specific URL.
    - **`or_terms`**: Alternative terms for an OR search, separated by spaces.
    - **`date_restrict`**: Limits results to documents published within a specific date range (e.g., 'd7' for last 7 days).
    - **`low_range`**: Specifies the lower bound for a numeric range search.
    - **`high_range`**: Specifies the upper bound for a numeric range search.
    - **`search_type`**: Specifies the type of search (e.g., 'image' for image search).
    - **`file_type`**: Restricts results to a specific file type (e.g., 'pdf').
    - **`rights`**: Filters results by usage rights (e.g., 'cc_publicdomain' for public domain content).
    - **`img_size`**: Specifies the desired image size for image search (e.g., 'medium', 'large').
    - **`img_type`**: Filters image search results by type (e.g., 'photo', 'clipart').
    - **`img_color_type`**: Specifies the desired color type in image search (e.g., 'blackandwhite', 'color').
    - **`img_dominant_color`**: Filters image search results by dominant color (e.g., 'red', 'blue').

    Returns:
    - A structured response containing keyword insights based on the provided search parameters.

    Usage example:
    ```
    GET /track?includes=python&count=5&sort=date
    ```
    """
    response = await KeywordService.fetch_batch_keyword_insight(db, params)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/twitter/track")
async def search_recent_tweets(
    params: TweetSearchParams = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Perform a recent search for tweets using the X API.

    The request body must include all the necessary parameters as defined in the TweetSearchParams model.
    """
    response = await XTweetSearchService.search_recent_tweets(db, params)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/web/sentiments",
    summary="Track Keyword Insights",
    description=(
        "This endpoint allows users to retrieve keyword insights from Google Custom Search. "
        "It supports a range of parameters for customizing the search query, including filters for keywords, "
        "phrases, languages, locations, and other advanced settings. Results can be paginated and "
        "further refined based on content type, usage rights, and image attributes."
    ),
    response_description="Returns keyword insights based on provided search parameters.",
)
async def get_keyword_sentiment(
    params: GoogleSearchParams = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Track Keyword Insights

    This endpoint allows users to query Google Custom Search for keyword insights with advanced filters.
    Provides keyword tracking functionality with customizable parameters.

    **Parameters**:
    - `includes`: List of keywords to include in the search query.
    - `excludes`: List of keywords to exclude from the search results.
    - **`phrases`**: List of exact phrases to include in the search, each phrase enclosed in double quotes.
    - **`locations`**: Domains or sites to restrict search results (e.g., 'site:example.com').
    - **`languages`**: Languages to restrict search results (e.g., 'lang_en' for English).
    - **`platforms`**: Specific sites or platforms to prioritize in the search query.
    - **`start_index`**: The starting index for pagination, typically a multiple of count (e.g., 1, 11, 21).
    - **`count`**: Number of results per page (between 1 and 10).
    - **`lr`**: Restricts results to documents in a specified language (e.g., 'lang_en' for English).
    - **`safe`**: Enables or disables safe search filtering ('active' or 'off').
    - **`cx`**: The Custom Search Engine ID to use for the request.
    - **`sort`**: The order of the search results (e.g., 'date' for most recent).
    - **`filter`**: Duplicate content filtering (1 to enable, 0 to disable).
    - **`gl`**: Geolocation country code to fine-tune results based on a location (e.g., 'US' for United States).
    - **`cr`**: Restricts search results to a specific country (e.g., 'countryUS' for United States).
    - **`googlehost`**: Specifies the Google domain to use (e.g., 'google.com' or 'google.co.uk').
    - **`c2coff`**: Disables translation between Simplified and Traditional Chinese ('1' to disable).
    - **`hq`**: Additional query terms to emphasize in the search.
    - **`hl`**: Interface language for the Google search engine (e.g., 'en' for English).
    - **`site_search`**: Restricts search results to a specific site (e.g., 'example.com').
    - **`site_search_filter`**: Site search filtering ('i' includes, 'e' excludes site from results).
    - **`exact_terms`**: Terms that must appear in search results exactly as provided.
    - **`exclude_terms`**: Terms to exclude from search results.
    - **`link_site`**: Restricts results to pages that link to a specific URL.
    - **`or_terms`**: Alternative terms for an OR search, separated by spaces.
    - **`date_restrict`**: Limits results to documents published within a specific date range (e.g., 'd7' for last 7 days).
    - **`low_range`**: Specifies the lower bound for a numeric range search.
    - **`high_range`**: Specifies the upper bound for a numeric range search.
    - **`search_type`**: Specifies the type of search (e.g., 'image' for image search).
    - **`file_type`**: Restricts results to a specific file type (e.g., 'pdf').
    - **`rights`**: Filters results by usage rights (e.g., 'cc_publicdomain' for public domain content).
    - **`img_size`**: Specifies the desired image size for image search (e.g., 'medium', 'large').
    - **`img_type`**: Filters image search results by type (e.g., 'photo', 'clipart').
    - **`img_color_type`**: Specifies the desired color type in image search (e.g., 'blackandwhite', 'color').
    - **`img_dominant_color`**: Filters image search results by dominant color (e.g., 'red', 'blue').

    Returns:
    - A structured response containing keyword insights based on the provided search parameters.

    Usage example:
    ```
    GET /track?includes=python&count=5&sort=date
    ```
    """
    response = await KeywordService.get_web_keyword_sentiment(db, params)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/web/post-type",
    summary="Post Type Frequency",
    description=(
        "This endpoint allows users to retrieve keyword post types frequency."
    ),
    response_description="Returns keyword post types based on provided search parameters.",
)
async def get_keyword_post_type(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.get_post_type_frequency(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/web/top-countries",
    summary="Post Country Frequency",
    description=(
        "This endpoint allows users to retrieve keyword post countries frequency."
    ),
    response_description="Returns keyword post countries based on provided search parameters.",
)
async def get_keyword_post_countries(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.get_country_code_frequency(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/web/top-platforms",
    summary="Post platforms Frequency",
    description=(
        "This endpoint allows users to retrieve keyword post platforms frequency."
    ),
    response_description="Returns keyword post platforms based on provided search parameters.",
)
async def get_keyword_post_platforms(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.get_platform_frequency_data(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/web/daily-frequency",
    summary="Post daily Frequency",
    description=(
        "This endpoint allows users to retrieve keyword post daily frequency."
    ),
    response_description="Returns keyword post daily mentions based on provided search parameters.",
)
async def get_keyword_post_daily_frequency(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.get_keyword_daily_frequency_data(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/web/top-words",
    summary="Top Words",
    description=("This endpoint allows users to retrieve keyword top words."),
    response_description="Returns keyword post top words or topics based on provided search parameters.",
)
async def get_keyword_top_words(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.get_word_cloud_data(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/twitter/mentions-insights",
    summary="Keyword Mentions",
    description=("This endpoint allows users to retrieve keyword mentions insight."),
    response_description="Returns keyword mentions based on provided search parameters.",
)
async def get_mentions_insights(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.process_mentions(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/twitter/posts",
    summary="Keyword Posts",
    description=("This endpoint allows users to retrieve keyword posts insight."),
    response_description="Returns keyword posts based on provided search parameters.",
)
async def get_posts(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.process_twitter_posts(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/twitter/top-countries",
    summary="Keyword Locations",
    description=("This endpoint allows users to retrieve keyword locations insight."),
    response_description="Returns keyword locations based on provided search parameters.",
)
async def get_locations(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.get_x_top_mentioned_countries(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/twitter/influencers",
    summary="Keyword Influencer",
    description=("This endpoint allows users to retrieve keyword influencers insight."),
    response_description="Returns keyword influencers based on provided search parameters.",
)
async def get_influencers(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.process_influencers(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/twitter/sentiments",
    summary="Keyword Sentiments",
    description=("This endpoint allows users to retrieve keyword sentiments insight."),
    response_description="Returns keyword sentiments based on provided search parameters.",
)
async def get_x_sentiments(
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.process_twitter_sentiments(db, cache_key)
    return UriResponse.get_status_response(response=response)


@router.get(
    "/sentiments/time/insight",
    summary="Keyword Sentiments Insight",
    description=(
        "This endpoint allows users to retrieve keyword sentiments over time."
    ),
    response_description="Returns keyword sentiments based on provided search parameters.",
)
async def get_sentiments_overtime(
    web_sentiment_cache_key: str = Query(
        ..., description="The unique web cache key for the query"
    ),
    twitter_sentiment_cache_key: Optional[str] = Query(
        None, description="The unique twitter cache key for the query"
    ),
    source_filter: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.get_keyword_sentiment_over_time(
        db, web_sentiment_cache_key, twitter_sentiment_cache_key, source_filter
    )
    return UriResponse.get_status_response(response=response)


@router.get(
    "/twitter/ai-conversation-insights",
    summary="Keyword Conversation Insights",
    description=(
        "This endpoint allows users to retrieve keyword conversation insight."
    ),
    response_description="Returns keyword conversations insights based on provided search parameters.",
)
async def get_keyword_conversation_insights(
    keyword: str,
    cache_key: str = Query(..., description="The unique cache key for the query"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    # Call the service method
    response = await KeywordService.process_keyword_conversation_insights(
        db, keyword, cache_key
    )
    return UriResponse.get_status_response(response=response)
