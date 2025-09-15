from typing import List, Literal, Optional
from pydantic import BaseModel
from fastapi import Query

from app.domain.enums.reddit_enum import RedditSearchSortEnum, RedditSearchTEnum


class RedditCommentsSearchParams(BaseModel):
    """
    Represents query parameters for a Reddit Custom Search request, allowing
    for robust keyword tracking with fine-tuned customization.

    Attributes:
        includes: List of keywords to include in the search query.
        excludes: List of keywords to exclude from the search results.
    """

    includes: Optional[List[str]] = Query(
        None, description="Keywords to include in the search"
    )
    excludes: Optional[List[str]] = Query(
        None, description="Keywords to exclude from the search"
    )


class RedditSearchParams(BaseModel):
    """
    Model for specifying Reddit search parameters with strict validation.

    Attributes:
        q (str): The search query string (required, max 512 characters).
        after (Optional[str]): Fullname of a thing for pagination.
        before (Optional[str]): Fullname of a thing for pagination.
        category (Optional[str]): A short string (max 5 characters).
        count (Optional[int]): A positive integer (default: 0).
        include_facets (Optional[bool]): Boolean flag to include facets.
        limit (Optional[int]): The maximum number of items desired (default: 25, max: 100).
        restrict_sr (Optional[bool]): Boolean flag to restrict search within subreddit.
        show (Optional[Literal['all']]): Optional filter to show 'all'.
        sort (Optional[Literal['relevance', 'hot', 'top', 'new', 'comments']]): Sorting order.
        sr_detail (Optional[bool]): Boolean flag to expand subreddit details.
        t (Optional[Literal['hour', 'day', 'week', 'month', 'year', 'all']]): Time filter.
        type (Optional[str]): Comma-delimited list of result types (sr, link, user).
    """

    q: str = Query(
        ..., max_length=512, description="The search query string (required)"
    )
    after: Optional[str] = Query(
        None, description="Fullname of a thing (for pagination)"
    )
    before: Optional[str] = Query(
        None, description="Fullname of a thing (for pagination)"
    )
    category: Optional[str] = Query(
        None, max_length=5, description="A string no longer than 5 characters"
    )
    count: Optional[int] = Query(0, ge=0, description="A positive integer (default: 0)")
    include_facets: Optional[bool] = Query(None, description="Boolean value")
    limit: Optional[int] = Query(
        25, ge=1, le=100, description="Max items (default: 25, max: 100)"
    )
    restrict_sr: Optional[bool] = Query(None, description="Boolean value")
    show: Optional[Literal["all"]] = Query(
        None, description="Optional: The string 'all'"
    )
    sort: Optional[RedditSearchSortEnum] = Query(None, description="Sort order")
    sr_detail: Optional[bool] = Query(None, description="Optional: Expand subreddits")
    t: Optional[RedditSearchTEnum] = Query(None, description="Time filter")
    type: Optional[str] = Query(
        None, description="Comma-delimited list of result types (sr, link, user)"
    )
    max_pages: int = 1

    class Config:
        use_enum_values = True
