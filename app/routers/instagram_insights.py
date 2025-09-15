from fastapi import APIRouter, Depends, Query
from app.services.GoogleService import GoogleService
from app.services.InstagramService import InstagramService
from app.services.InstagramHashtagService import InstagramHashtagService
from app.domain.responses.uri_response import UriResponse
from app.domain.requests.instagram_requests import (
    PostInstagramMediaRequest,
    InstagramInsightsRequest,
    CommentSentimentRequest,
)
from app.dependencies import (
    enforce_feature_limit,
    get_db_dependency,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from typing import Optional, List
from app.core.auth_handler import get_meta_access_token
from fastapi.encoders import jsonable_encoder

router = APIRouter()


@router.get("/user/insights")
async def fetch_instagram_user_insights(
    ig_user_id: Optional[str] = None,
    metrics: Optional[str] = "impressions,reach",
    period: Optional[str] = "day, week, days_28",
    since: Optional[str] = None,
    until: Optional[str] = None,
    meta_access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramService.fetch_instagram_user_insights(
        ig_user_id, metrics, period, meta_access_token, since, until
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/media/no-breakdown/post_insights")
async def fetch_instagram_media_insights(
    media_id: str,
    metrics: Optional[
        str
    ] = "plays,clips_replays_count,ig_reels_video_view_total_time,ig_reels_avg_watch_time,ig_reels_aggregated_all_plays_count,comments,likes,reach,saved,shares,total_interactions",
    since: Optional[str] = None,
    until: Optional[str] = None,
    meta_access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramService.fetch_instagram_media_insights(
        media_id=media_id,
        metrics=metrics,
        access_token=meta_access_token,
        since=since,
        until=until,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/media/with-breakdown/post_insights")
async def fetch_instagram_breakdown_media_insights(
    media_id: str,
    metrics: Optional[
        str
    ] = "comments, reach, saved, likes, shares, total_interactions",
    since: Optional[str] = None,
    until: Optional[str] = None,
    meta_access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramService.fetch_instagram_media_insights(
        media_id=media_id,
        metrics=metrics,
        access_token=meta_access_token,
        since=since,
        until=until,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/user/insights/interaction-metrics",
    summary="Fetch Instagram User Interaction Metrics",
    tags=["Instagram Insights"],
)
async def fetch_instagram_user_insights_interaction_metrics(
    ig_user_id: Optional[str] = None,
    metrics: Optional[str] = "likes,comments",
    metric_type: Optional[str] = None,
    breakdown: Optional[str] = None,
    period: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    meta_access_token: str = Depends(get_meta_access_token),
):
    """
    Fetches interaction metrics for the Instagram user, providing insights on interactions such as likes, comments, shares, and more.

    **Available Metrics**:
    1. **impressions**: The number of times your posts, stories, reels, videos, and live videos were on screen, including in ads.
    2. **reach**: The number of unique accounts that have seen your content, including in ads. Reach is different from impressions as it counts unique views.
    3. **total_interactions**: The total number of interactions on posts, stories, reels, videos, and live videos.
    4. **accounts_engaged**: The number of accounts that have interacted with your content, including likes, saves, comments, shares, or replies.
    5. **likes**: The number of likes on your posts, reels, and videos.
    6. **comments**: The number of comments on your posts, reels, videos, and live videos.
    7. **saved**: The number of saves of your posts, reels, and videos.
    8. **shares**: The number of shares of your posts, stories, reels, videos, and live videos.
    9. **replies**: The number of replies you received from your stories.
    10. **follows_and_unfollows**: The number of accounts that followed or unfollowed you in the selected period.
    11. **profile_links_taps**: The number of taps on your business address, call button, email button, and text button.
    12. **website_clicks**: The number of times the link to your website was tapped.
    13. **profile_views**: The number of times your profile was visited.

    **Parameters**:
    - `ig_user_id`: The Instagram user ID for which metrics are to be fetched.
    - `metrics`: A comma-separated list of metrics to retrieve (e.g., "likes,comments"). Default is 'likes,comments'.
    - `metric_type`: The type of the metric (e.g., total_value, time_series). Certain metrics support different types.
    - `breakdown`: Breakdown of the data for specific metrics (e.g., media_product_type, follow_type, contact_button_type).
    - `period`: The period for the metrics (e.g., day). Default is 'day'.
    - `since`: Optional start date in UNIX timestamp format for time-bound metrics.
    - `until`: Optional end date in UNIX timestamp format for time-bound metrics.
    - `meta_access_token`: Meta (Facebook) access token for authorization.

    **Notes**:
    - Metrics such as **reach** and **accounts_engaged** are estimated and in development.
    - `follows_and_unfollows` is not returned if the IG user has fewer than 100 followers.
    - The `metric_type` and `breakdown` parameters may be required for certain metrics like **reach** and **likes**.

    **Example Response**:
    ```
    {
        "status": true,
        "responseCode": 200,
        "responseMessage": "user interaction insight successfully retrieved.",
        "responseData": [
            {
                "name": "likes",
                "period": "day",
                "total_value": 125
            },
            {
                "name": "comments",
                "period": "day",
                "total_value": 34
            }
        ]
    }
    ```

    **Returns**:
    - A JSON response containing interaction insights or an error response if the request fails.
    """
    response = await InstagramService.fetch_instagram_user_insights_interaction_metrics(
        ig_user_id=ig_user_id,
        metrics=metrics,
        metric_type=metric_type,
        breakdown=breakdown,
        period=period,
        user_facebook_access_token=meta_access_token,
        since=since,
        until=until,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/user/insights/demographic-metrics",
    summary="Fetch Instagram User Demographic Metrics",
    tags=["Instagram Insights"],
)
async def fetch_instagram_user_demographic_metrics(
    ig_user_id: Optional[str] = None,
    metrics: Optional[
        str
    ] = "engaged_audience_demographics,reached_audience_demographics,follower_demographics",
    metric_type: Optional[str] = "total_value",
    breakdowns: Optional[str] = "age,gender",
    period: Optional[str] = "lifetime",
    timeframe: Optional[str] = "this_month",
    since: Optional[str] = None,
    until: Optional[str] = None,
    meta_access_token: str = Depends(get_meta_access_token),
):
    """
    Fetches demographic insights for the Instagram user, including metrics for engaged, reached, and follower demographics.

    **Available Metrics**:
    1. **engaged_audience_demographics**: Demographic characteristics of the engaged audience, including countries, cities, age, and gender distribution.
    2. **reached_audience_demographics**: Demographic characteristics of the reached audience, including countries, cities, age, and gender distribution.
    3. **follower_demographics**: Demographic characteristics of followers, including countries, cities, age, and gender distribution.

    **Parameters**:
    - `ig_user_id`: The Instagram user ID for which metrics are to be fetched.
    - `metrics`: The demographic metric to retrieve. Default is 'engaged_audience_demographics'. Can also be 'reached_audience_demographics' or 'follower_demographics'.
    - `metric_type`: The type of the metric (e.g., total_value). Default is 'total_value'.
    - `breakdowns`: Breakdown of the data (e.g., country, city, age, gender). Default is 'country'.
    - `period`: Period for the metric (e.g., lifetime). Default is 'lifetime'.
    - `timeframe`: Timeframe for the data (e.g., this_month, this_week). Default is 'this_month'.
    - `since`: Optional start date in UNIX timestamp format. **Note**: Not supported for demographic metrics.
    - `until`: Optional end date in UNIX timestamp format. **Note**: Not supported for demographic metrics.
    - `meta_access_token`: Meta (Facebook) access token for authorization.

    **Notes**:
    - These metrics do not support custom date ranges with `since` and `until`.
    - `this_month` returns data for the last 30 days, and `this_week` returns data for the last 7 days.
    - The metrics will not return data if the IG user has fewer than 100 audience members during the selected timeframe.
    - The timeframes 'last_14_days', 'last_30_days', 'last_90_days', and 'prev_month' will no longer be supported beginning with version 20.0 of the API.

    **Example Response**:
    ```
    {
      "status": true,
      "responseCode": 200,
      "responseMessage": "demography insight successfully retrieved.",
      "responseData": [
        {
          "name": "engaged_audience_demographics",
          "period": "lifetime",
          "title": "Engaged audience demographics",
          "description": "The demographic characteristics of the engaged audience, including countries, cities and gender distribution.",
          "total_value": {
            "breakdowns": [
              {
                "dimension_keys": [
                  "country"
                ],
                "results": [
                  {
                    "dimension_values": ["US"],
                    "value": 14
                  },
                  {
                    "dimension_values": ["GB"],
                    "value": 9
                  },
                  {
                    "dimension_values": ["NG"],
                    "value": 115
                  },
                  {
                    "dimension_values": ["CA"],
                    "value": 8
                  }
                  // other countries...
                ]
              }
            ]
          },
          "id": "17841464129861404/insights/engaged_audience_demographics/lifetime"
        }
      ]
    }
    ```

    **Returns**:
    - A JSON response containing demographic insights or an error response if the request fails.
    """
    response = await InstagramService.fetch_instagram_demographic_metrics(
        ig_user_id,
        metrics,
        metric_type,
        breakdowns,
        period,
        timeframe,
        meta_access_token,
        since,
        until,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/cached/user/insights")
async def get_cached_instagram_insights(
    user_id: str,
    ig_user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await InstagramService.get_instagram_insights(user_id, ig_user_id, db)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.put("/{ig_user_id}/insights/update")
async def update_instagram_insights(
    request: InstagramInsightsRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await InstagramService.fetch_instagram_user_insights(
        instagram_user_id=request.influencer_id,
        user_facebook_access_token=request.access_token,
        metrics=request.metrics,
        period=request.period,
        since=request.since,
        until=request.until,
    )
    return await InstagramService.update_instagram_insights(
        "user_id_placeholder", request.ig_user_id, data, db
    )


@router.delete("/{ig_user_id}/insights/delete")
async def delete_instagram_insights(
    ig_user_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    return InstagramService.delete_instagram_insights(
        "user_id_placeholder", ig_user_id, db
    )


@router.get("/hashtag-search")
async def search_instagram_hashtag(
    hashtag: str,
    fields: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    after: Optional[str] = Query(None),
):
    response = await InstagramService.fetch_hashtag_search(
        keyword=hashtag, fields=fields, since=since, until=until, after=after
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/save-instagram-account")
async def save_instagram_account(
    user_id: str,
    meta_access_token: str = Depends(get_meta_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    account_limits: dict = Depends(enforce_feature_limit),
):
    if account_limits and account_limits.get("responseCode") == 400:
        return UriResponse.get_status_response(
            response=account_limits, status_code=account_limits.get("responseCode", "")
        )
    data = await InstagramService.save_instagram_account(
        user_id=user_id,
        access_token=meta_access_token,
        db=db,
        account_limits=account_limits,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/auth-business-discovery")
async def instagram_auth_business_discovery(
    username: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    before: Optional[str] = Query(None),
    after: Optional[str] = Query(None),
    meta_access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramService.fetch_auth_business_discovery(
        db, username, access_token=meta_access_token, before=before, after=after
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/batch-business-discovery")
async def batch_instagram_business_discovery(
    ig_usernames: List[str] = Query(None),
    before: Optional[str] = Query(None),
    after: Optional[str] = Query(None),
):
    response = await InstagramService.fetch_batch_business_discovery(
        ig_usernames=ig_usernames, before=before, after=after
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/anonymous-business-discovery")
async def anonymous_instagram_business_discovery(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    username: str = Query(None),
    before: Optional[str] = Query(None),
    after: Optional[str] = Query(None),
):
    response = await InstagramService.fetch_anonymous_business_discovery(
        db, username=username, before=before, after=after
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/business-discovery")
async def instagram_business_discovery(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    username: str = Query(),
    meta_access_token: Optional[str] = Query(None),
):
    response = await InstagramService.fetch_business_discovery(
        db, username=username, access_token=meta_access_token
    )

    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )


@router.post("/media/comment-sentiment")
async def instagram_business_media_comment_sentiment(request: CommentSentimentRequest):
    data = await GoogleService.analyze_comments_sentiment(request.comments, "caption")

    response = UriResponse.get_single_data_response("comment sentiment", data)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/tags")
async def fetch_business_tags(
    ig_user_id: str,
    after: Optional[str] = None,
    meta_access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramService.fetch_instagram_business_tags(
        meta_access_token, ig_user_id, after
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/stories")
async def fetch_business_stories(
    ig_user_id: str, meta_access_token: str = Depends(get_meta_access_token)
):
    response = await InstagramService.fetch_business_stories(
        meta_access_token, ig_user_id
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/media")
async def fetch_business_media(
    ig_user_id: str,
    next: Optional[str] = None,
    meta_access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramService.fetch_business_media(
        meta_access_token, ig_user_id, next
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/mentioned_comment")
async def fetch_business_mentions(
    ig_user_id: str,
    comment_id: str,
    meta_access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramService.fetch_business_mentioned_comment(
        meta_access_token, ig_user_id, comment_id
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/media/comments")
async def fetch_business_media_comments(
    ig_media_id: str, meta_access_token: str = Depends(get_meta_access_token)
):
    response = await InstagramService.fetch_business_media_comments(
        ig_media_id, meta_access_token
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/media/mentions")
async def fetch_business_media_mentions(
    ig_user_id: str,
    media_id: str,
    meta_access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramService.fetch_business_media_mentions(
        ig_user_id, media_id, meta_access_token
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/comment/replies/insights")
async def fetch_business_media_comment_insights(
    ig_comment_id: str, meta_access_token: str = Depends(get_meta_access_token)
):
    response = await InstagramService.fetch_business_comment_replies(
        ig_comment_id, meta_access_token
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/keyword-tracking")
async def track_hashtag(
    keyword: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramHashtagService.track_hashtag(keyword, db, access_token)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/hashtag/search",
    summary="Fetch Instagram Hashtag ID",
    tags=["Instagram Hashtags"],
)
async def fetch_instagram_hashtag_id(
    query: str,
    access_token: Optional[str] = Depends(get_meta_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Searches for a hashtag on Instagram and retrieves the hashtag ID.

    **Parameters**:
    - `query`: The name of the hashtag to search (without the # symbol).
    - `access_token`: Meta (Facebook) access token for authorization. Defaults to your app's system token if not provided.

    **Example Response**:
    ```
    {
        "status": true,
        "responseCode": 200,
        "responseMessage": "hashtag id successfully retrieved.",
        "responseData": {
            "id": "17843857450040591"
        }
    }
    ```

    **Returns**:
    - A JSON response containing the Instagram hashtag ID or an error response if the request fails.
    """
    response = await InstagramHashtagService.fetch_instagram_hashtag_id(
        query, db, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/hashtag/media",
    summary="Fetch Instagram Hashtag Media",
    tags=["Instagram Hashtags"],
)
async def fetch_instagram_hashtag_media(
    hashtag_id: str,
    media_type: str = "top_media",
    after: Optional[str] = None,
    before: Optional[str] = None,
    access_token: Optional[str] = Depends(get_meta_access_token),
):
    """
    Retrieves media associated with a specific Instagram hashtag (top or recent media).

    **Parameters**:
    - `hashtag_id`: The ID of the hashtag to retrieve media for.
    - `media_type`: Type of media to retrieve. Default is 'top_media'. Options are:
      - `top_media`: Returns the most popular media tagged with the hashtag.
      - `recent_media`: Returns the most recent media tagged with the hashtag.
    - `after`: Pagination cursor for fetching newer media.
    - `before`: Pagination cursor for fetching older media.
    - `access_token`: Meta (Facebook) access token for authorization. Defaults to your app's system token if not provided.

    **Example Response**:
    ```
    {
        "status": true,
        "responseCode": 200,
        "responseMessage": "hashtag media successfully retrieved.",
        "responseData": {
            "media": [
                {
                    "id": "17880997618081620",
                    "media_type": "IMAGE",
                    "comments_count": 84,
                    "like_count": 177
                },
                {
                    "id": "17871527143187462",
                    "media_type": "IMAGE",
                    "comments_count": 24,
                    "like_count": 57
                }
            ],
            "paging": {
                "cursors": {
                    "after": "NTAyYmE4..."
                },
                "next": "https://graph.facebook.com/..."
            }
        }
    }
    ```

    **Returns**:
    - A JSON response containing media data or an error response if the request fails.
    """
    response = await InstagramHashtagService.fetch_hashtag_media(
        instagram_hashtag_id=hashtag_id,
        access_token=access_token,
        fields=None,  # Optional, defaults to all fields
        after=after,
        before=before,
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/ai-media-report")
async def media_ai_reports(
    cache_key: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await InstagramService.fetch_ai_post_report(db, cache_key)

    return UriResponse.get_status_response(
        response=data, status_code=data["responseCode"]
    )


@router.post(
    "/media",
    summary="Post Media on Instagram",
    tags=["Instagram Hashtags"],
)
async def post_media(
    ig_user_id: str,
    payload: PostInstagramMediaRequest,
    access_token: str = Depends(get_meta_access_token),
):
    response = await InstagramService.publish_media_post(
        ig_user_id=ig_user_id, payload=payload, access_token=access_token
    )
    print("\nResponse: ", response)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/mentioned-comment", tags=["Instagram Mentioned Comment"])
async def fetch_mentioned_comment(
    ig_user_id: str,
    comment_id: str,
    meta_access_token: str = Depends(get_meta_access_token),
):
    """
    Fetch Instagram Comment in which the user was mentioned.

    **Parameters**:
    - `ig_user_id`: The Instagram User ID.
    - `comment_id`: The Comment ID where the user was mentioned.
    - `meta_access_token`: User's Instagram access token.

    **Returns**:
    JSON data containing the mentioned comment.
    """
    response = await InstagramService.fetch_mentioned_comment(
        meta_access_token, ig_user_id, comment_id
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
