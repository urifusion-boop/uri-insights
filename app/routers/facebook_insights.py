from fastapi import APIRouter, Depends, Query, Request
from app.services.FacebookService import FacebookService
from app.domain.responses.uri_response import UriResponse
from typing import Optional
from app.domain.requests.facebook_requests import (
    FacebookPostPayload,
    FacebookUpdatePostPayload,
    FacebookPhotoPayload,
    FacebookVideoPayload,
    FacebookReelVideoPayload,
)
from app.core.auth_handler import get_meta_access_token
from app.dependencies import get_db_dependency
from motor.motor_asyncio import AsyncIOMotorDatabase


router = APIRouter()


@router.get("/business-discovery")
async def fetch_business_discovery(
    page_id: str,
    before: Optional[str] = Query(None),
    after: Optional[str] = Query(None),
    meta_access_token: str = Depends(get_meta_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await FacebookService.fetch_facebook_page_discovery(
        page_id, meta_access_token, db, before, after
    )

    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )


@router.get("/pages")
async def fetch_user_facebook_pages(request: Request):
    headers = request.headers
    access_token = headers.get("Meta-Access-Token")

    response = await FacebookService.get_user_accounts(access_token)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/page/insights", summary="Fetch Facebook Page Insights")
async def get_facebook_page_insights(
    page_id: str,
    period: Optional[str] = Query(
        "day",
        description="The period for the metrics (e.g., day, week, month, lifetime). Default is 'day'.",
    ),
    metrics: str = Query(
        "page_post_engagements,page_follows,page_impressions,page_posts_impressions",
        description=(
            "Comma-separated list of metrics to retrieve. "
            "Examples: 'page_post_engagements,page_impressions'."
        ),
    ),
    since: Optional[str] = Query(
        None,
        description="Optional start date in UNIX timestamp format for time-bound metrics.",
    ),
    until: Optional[str] = Query(
        None,
        description="Optional end date in UNIX timestamp format for time-bound metrics.",
    ),
    previous: Optional[str] = Query(
        None,
        description="Cursor for paginated results to fetch the previous set of data.",
    ),
    next: Optional[str] = Query(
        None, description="Cursor for paginated results to fetch the next set of data."
    ),
    access_token: str = Depends(get_meta_access_token),
):
    """
    Fetch interaction metrics for a Facebook Page.

    **Available Metrics**:
    - **page_impressions**: Total number of times the page content was displayed.
    - **page_post_engagements**: Number of engagements with page posts (likes, shares, comments).
    - **page_follows**: Number of new follows to the page.
    - **page_views_total**: Total number of views on the page.
    - **page_posts_impressions**: Total impressions of posts from the page.

    **Parameters**:
    - `page_id`: The Facebook Page ID for which metrics are to be fetched.
    - `metrics`: A comma-separated list of metrics to retrieve. Default: `page_post_engagements,page_follows,page_impressions,page_posts_impressions`.
    - `period`: The period for the metrics (e.g., day, week, month, lifetime). Default: `day`.
    - `since`: Optional start date in UNIX timestamp format for time-bound metrics.
    - `until`: Optional end date in UNIX timestamp format for time-bound metrics.
    - `previous`: Cursor to fetch the previous set of paginated data.
    - `next`: Cursor to fetch the next set of paginated data.
    - `access_token`: Meta (Facebook) access token for authorization.

    **Notes**:
    - Some metrics may require specific permissions or access levels.
    - Paginated results are supported via `previous` and `next` cursors.
    """
    response = await FacebookService.fetch_facebook_insights(
        entity_id=page_id,
        metrics=metrics,
        since=since,
        until=until,
        previous=previous,
        next=next,
        period=period,
        access_token=access_token,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/page/search")
async def search_facebook_pages(
    name: str,
    fields: Optional[str] = Query(None),
    access_token: str = Depends(get_meta_access_token),
):
    response = await FacebookService.search_facebook_pages(
        access_token, name=name, fields=fields
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/post/insights")
async def get_facebook_post_insights(
    post_id: str,
    period: str = "lifetime",
    metrics: str = Query(
        "post_impressions,post_impressions_unique,post_engaged_users,post_clicks,post_clicks_unique,post_reactions_by_type_total,post_video_avg_time_watched,post_video_complete_views_30s,post_video_views,post_video_views_10s,post_video_views_unique"
    ),
    access_token: str = Depends(get_meta_access_token),
):
    response = await FacebookService.fetch_facebook_post_insights(
        post_id=post_id,
        metrics=metrics,
        period=period,
        access_token=access_token,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/video/insights",
    summary="Get Facebook Video Insights",
    description=(
        "Retrieve insights for a specific Facebook video or reel. "
        "Supports both reel-specific metrics and general video metrics. "
        "Refer to the documentation for the list of available metrics."
    ),
    tags=["Facebook Insights"],
)
async def get_facebook_video_insights(
    video_id: str = Query(..., description="The ID of the Facebook video or reel."),
    period: str = Query(
        "lifetime",
        description=(
            "The period for which the insights are retrieved. "
            "Default is 'lifetime'. Other supported periods depend on the metric."
        ),
    ),
    metrics: Optional[str] = Query(
        None,
        description=(
            "Comma-separated list of metrics to retrieve. If not specified, default metrics will be used. "
            "Refer to the 'Available Metrics' section below for more details."
        ),
    ),
    access_token: str = Depends(get_meta_access_token),
):
    """
    ### Available Metrics
    #### **Reel-Specific Metrics**
    - **`blue_reels_play_count`**: Total play count for reels.
    - **`fb_reels_replay_count`**: Total replay count for reels.
    - **`fb_reels_total_plays`**: Total play count across all distribution channels.
    - **`post_impressions_unique`**: Unique impressions of the reel.
    - **`post_video_avg_time_watched`**: Average time viewers spent watching the reel.
    - **`post_video_followers`**: Total followers gained from the reel.
    - **`post_video_likes_by_reaction_type`**: Breakdown of likes by reaction type.
    - **`post_video_retention_graph`**: Retention graph for reel views.
    - **`post_video_social_actions`**: Social actions (likes, comments, shares).
    - **`post_video_view_time`**: Total time viewers spent watching the reel.

    #### **General Video Metrics**
    - **`total_video_views`**: Total number of times the video was viewed for at least 3 seconds.
    - **`total_video_views_unique`**: Total unique viewers for at least 3 seconds.
    - **`total_video_views_autoplayed`**: Number of times the video auto-played for 3+ seconds.
    - **`total_video_views_clicked_to_play`**: Number of times the video played after a user clicked play.
    - **`total_video_views_organic`**: Number of organic video views for 3+ seconds.
    - **`total_video_views_paid`**: Number of paid video views for 3+ seconds.
    - **`total_video_complete_views`**: Number of times the video was watched to 97% or more.
    - **`total_video_10s_views`**: Number of times the video was viewed for 10 seconds or more.
    - **`total_video_avg_time_watched`**: Average time viewers spent watching the video.
    - **`total_video_view_total_time`**: Total time viewers spent watching the video.
    - **`total_video_retention_graph`**: Retention graph for video views over time.
    - **`total_video_reactions_by_type_total`**: Total reactions to the video, broken down by type.
    - **`total_video_view_time_by_age_bucket_and_gender`**: Total view time by age and gender.
    - **`total_video_views_by_country_id`**: Lifetime video views by country.

    ### How to Use
    - Pass the `reel_id` of the video or reel you want to analyze.
    - Specify `metrics` as a comma-separated list to retrieve specific insights.
    - Use `period` to filter insights based on supported periods (default: 'lifetime').
    """
    response = await FacebookService.fetch_videos_insight(
        video_id=video_id,
        access_token=access_token,
        metrics=metrics,
        period=period,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", 200)
    )


@router.get("/photos/insights")
async def get_facebook_photo_insights(
    photo_id: str,
    period: str,
    metrics: str = Query("impressions"),
    since: Optional[str] = None,
    until: Optional[str] = None,
    previous: Optional[str] = None,
    next: Optional[str] = None,
    access_token: str = Depends(get_meta_access_token),
):
    response = await FacebookService.fetch_facebook_insights(
        entity_id=photo_id,
        metrics=metrics,
        since=since,
        until=until,
        previous=previous,
        next=next,
        period=period,
        access_token=access_token,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/page/audience-demographics",
    summary="Retrieve Audience Demographics for a Facebook Page",
    description="Fetch audience demographics insights for a Facebook Page, including gender, age, country, and city breakdowns.",
)
async def get_audience_demographics(
    page_id: str = Query(..., description="The ID of the Facebook Page."),
    metrics: str = Query(
        "page_fans_country,page_fans_city",
        description="Metrics to retrieve, separated by commas.",
    ),
    access_token: str = Depends(get_meta_access_token),
):
    """
    Retrieve audience demographics insights for a Facebook Page.
    """
    response = await FacebookService.fetch_demographic_insights(
        page_id=page_id, metrics=metrics, access_token=access_token
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/page/posts")
async def get_facebook_page_feed(
    previous: Optional[str] = None,
    next: Optional[str] = None,
    access_token: str = Depends(get_meta_access_token),
):
    response = await FacebookService.fetch_facebook_page_posts(
        previous=previous,
        next=next,
        access_token=access_token,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/page/stories")
async def get_facebook_page_stories(
    page_id: str = Query(..., description="The ID of the Facebook Page."),
    previous: Optional[str] = None,
    next: Optional[str] = None,
    access_token: str = Depends(get_meta_access_token),
):
    response = await FacebookService.fetch_facebook_page_stories(
        page_id=page_id,
        access_token=access_token,
        previous=previous,
        next=next,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/page/reels")
async def get_facebook_page_reels(
    page_id: str = Query(..., description="The ID of the Facebook Page."),
    previous: Optional[str] = None,
    next: Optional[str] = None,
    access_token: str = Depends(get_meta_access_token),
):
    response = await FacebookService.fetch_facebook_page_reels(
        page_id=page_id,
        access_token=access_token,
        previous=previous,
        next=next,
    )

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get(
    "/page/mentions",
    summary="Retrieve Mentions for a Facebook Page",
    description="Fetch posts where your Facebook Page has been mentioned, including media, comments, likes, and shares.",
)
async def get_facebook_mentions(
    page_id: str = Query(..., description="The ID of the Facebook page."),
    previous: Optional[str] = Query(None, description="Start time in ISO 8601 format."),
    next: Optional[str] = Query(None, description="End time in ISO 8601 format."),
    access_token: str = Depends(get_meta_access_token),
):
    """
    Retrieve mentions for a Facebook Page with detailed metadata.
    """
    response = await FacebookService.fetch_facebook_mentions(
        page_id=page_id,
        access_token=access_token,
        previous=previous,
        next=next,
    )

    return response


@router.get(
    "/page/tags",
    summary="Retrieve Mentions for a Facebook Page",
    description="Fetch posts where your Facebook Page has been tagged, including media, comments, likes, and shares.",
)
async def get_facebook_tags(
    page_id: str = Query(..., description="The ID of the Facebook page."),
    since: Optional[str] = Query(None, description="Start time in ISO 8601 format."),
    until: Optional[str] = Query(None, description="End time in ISO 8601 format."),
    limit: Optional[int] = Query(
        25, description="Number of tags to retrieve per page."
    ),
    access_token: str = Depends(get_meta_access_token),
):
    """
    Retrieve tags for a Facebook Page with detailed metadata.
    """
    response = await FacebookService.fetch_facebook_tags(
        page_id=page_id,
        access_token=access_token,
        since=since,
        until=until,
        limit=limit,
    )

    return response


@router.post(
    "/post",
    summary="Publish a Facebook Post",
    tags=["Facebook Posts"],
)
async def publish_facebook_post(
    page_id: str,
    payload: FacebookPostPayload,
    access_token: str = Depends(get_meta_access_token),
):
    """
    Publishes a new post to a specified Facebook Page.

    **Parameters**:
    - `page_id` (query, required): The ID of the Facebook Page where the post will be published.
    - `payload` (body, required):
        - `message` (optional, string): The text content of the post.
        - `link` (optional, string): A URL to include in the post.
        - `published` (optional, boolean, default: `true`): Whether to publish the post immediately.
        - `attached_media` (optional, dict): Media IDs gotten from photo or image upload endpoints.
        - `scheduled_publish_time` (optional, integer): UNIX timestamp for scheduling the post.
        - `targeting` (optional, dict): Audience targeting options (e.g., `geo_locations`).

    **Example Request Body**:
    ```json
    {
      "message": "Check out our latest update!",
      "link": "https://example.com",
      "published": true,
      "scheduled_publish_time": 1700000000,
       "attached_media": [
            { "media_fbid": "12332435" },
            { "media_fbid": "31334242" }
        ],
      "targeting": {
        "geo_locations": {
          "countries": ["US"]
        }
      }
    }
    ```

    **Example Response**:
    ```json
    {
      "status": true,
      "responseCode": 200,
      "responseData": {
        "id": "123456789_987654321"
      }
    }
    ```

    **Notes**:
    - If `scheduled_publish_time` is provided, `published` must be set to `false`.
    - Targeting options depend on Meta API capabilities.

    **Returns**:
    - `id` (string): The ID of the newly created post.
    """
    response = await FacebookService.publish_post(page_id, payload, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.put(
    "/post/{post_id}",
    summary="Update a Facebook Post",
    tags=["Facebook Posts"],
)
async def update_facebook_post(
    post_id: str,
    payload: FacebookUpdatePostPayload,
    access_token: str = Depends(get_meta_access_token),
):
    """
    Updates the text content of an existing post on a Facebook Page.

    **Parameters**:
    - `post_id` (path, required): The ID of the post to update.
    - `payload` (body, required):
        - `message` (required, string): The updated text content of the post.

    **Example Request Body**:
    ```json
    {
      "message": "Updated post content"
    }
    ```

    **Example Response**:
    ```json
    {
      "status": true,
      "responseCode": 200,
      "responseData": {
        "success": true
      }
    }
    ```

    **Notes**:
    - Only posts created by the app can be updated.

    **Returns**:
    - `success` (boolean): Indicates whether the update was successful.
    """
    response = await FacebookService.update_post(post_id, payload, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post(
    "/photo",
    summary="Upload a Photo to a Facebook Page",
    tags=["Facebook Media"],
)
async def upload_facebook_photo(
    page_id: str,
    payload: FacebookPhotoPayload,
    access_token: str = Depends(get_meta_access_token),
):
    """
    Uploads a photo to a specified Facebook Page.

    **Parameters**:
    - `page_id` (query, required): The ID of the Facebook Page where the photo will be uploaded.
    - `payload` (body, required):
        - `url` (required, string): URL of the photo to upload.
        - `caption` (optional, string): A caption for the photo.
        - `published` (optional, bool): Whether post should be published immediately.

    **Example Request Body**:
    ```json
    {
      "url": "https://example.com/photo.jpg",
      "caption": "Check out this amazing photo!",
      "published": true
    }
    ```

    **Example Response**:
    ```json
    {
      "status": true,
      "responseCode": 200,
      "responseData": {
        "id": "photo_id",
        "post_id": "page_post_id"
      }
    }
    ```

    **Returns**:
    - `id` (string): The ID of the uploaded photo.
    - `post_id` (string): The ID of the corresponding Facebook post.
    """
    response = await FacebookService.upload_photo(page_id, payload, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post(
    "/video",
    summary="Upload a Video large than 1gb to a Facebook Page",
    tags=["Facebook Media"],
)
async def upload_facebook_large_sized_video(
    page_id: str,
    payload: FacebookVideoPayload,
    access_token: str = Depends(get_meta_access_token),
):
    """
    Uploads a large video (above 1gb) to a specified Facebook Page.

    **Parameters**:
    - `page_id` (query, required): The ID of the Facebook Page where the video will be uploaded.
    - `payload` (body, required):
        - `title` (required, string): The title of the video.
        - `description` (optional, string): A description for the video.
        - `video_handle` (required, string): The handle received after uploading the video.
        - `file_data` (optional, dict): Information containing file_name, file_length, file_type.


    **Example Request Body**:
    ```json
    {
      "title": "New Video!",
      "description": "This is a test video.",
      "video_handle": "upload_handle_here",
      "file_data": {
        "file_name": "The name of the file",
        "file_length": "File size in bytes",
        "file_type": "The file's MIME type. Valid values are: application/pdf, image/jpeg, image/jpg, image/png, and video/mp4"
      }
    }
    ```

    **Example Response**:
    ```json
    {
      "status": true,
      "responseCode": 200,
      "responseData": {
        "id": "video_id"
      }
    }
    ```

    **Returns**:
    - `id` (string): The ID of the uploaded video.
    """
    response = await FacebookService.resumable_video_upload(
        page_id, payload, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post(
    "/simple_video",
    summary="Upload a Video below 1gb to a Facebook Page",
    tags=["Facebook Media"],
)
async def upload_facebook_small_sized_video(
    page_id: str,
    payload: FacebookVideoPayload,
    access_token: str = Depends(get_meta_access_token),
):
    """
    Uploads a video to a specified Facebook Page.

    **Parameters**:
    - `page_id` (query, required): The ID of the Facebook Page where the video will be uploaded.
    - `payload` (body, required):
        - `title` (required, string): The title of the video.
        - `description` (optional, string): A description for the video.
        - `video_url` (required, string): The url pointing to the video.


    **Example Request Body**:
    ```json
    {
      "title": "New Video!",
      "description": "This is a test video.",
      "video_url": "video_url_here",
    }
    ```

    **Example Response**:
    ```json
    {
      "status": true,
      "responseCode": 200,
      "responseData": {
        "id": "video_id"
      }
    }
    ```

    **Returns**:
    - `id` (string): The ID of the uploaded video.
    """
    response = await FacebookService.simple_video_upload(page_id, payload, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# @router.post(
#     "/multiple_media",
#     summary="Upload multiple photos or videos to a Facebook Page",
#     tags=["Facebook Media"],
# )
# async def upload_multiple_media(
#     page_id: str,
#     payload: FacebookMultipleMediaPayload,
#     access_token: str = Depends(get_meta_access_token),
# ):
#     """
#     Uploads multiple photos or videos to a specified Facebook Page.

#     **Parameters**:
#     - `page_id` (query, required): The ID of the Facebook Page where the media will be uploaded.
#     - `payload` (body, required):
#         - `attached_media` (optional, list): A list of media items to attach to the post.
#             - **Photo**:
#               - `url` (required, string): The URL of the photo to upload.
#               - `caption` (optional, string): Caption for the photo.
#               - `published` (optional, boolean): Whether to publish immediately (default: True).
#             - **Video**:
#               - `title` (required, string): The title of the video.
#               - `description` (optional, string): A description for the video.
#               - `video_url` (required, string): The URL pointing to the video file.
#               - `file_data` (optional, object): File data for uploading the video.
#         - `message` (optional, string): Text content for the post.
#         - `link` (optional, string): A URL to include in the post.
#         - `published` (optional, boolean): Whether to publish immediately (default: True).
#         - `scheduled_publish_time` (optional, integer): UNIX timestamp for scheduling the post.
#         - `targeting` (optional, object): Audience targeting options.

#     **Example Request Body**:
#     ```json
#     {
#       "attached_media": [
#         { "url": "https://example.com/image1.jpg", "caption": "Photo 1" },
#         { "title": "Test Video", "video_url": "https://example.com/video.mp4" }
#       ],
#       "message": "Check out our latest updates!",
#       "link": "https://example.com",
#       "published": true
#     }
#     ```

#     **Example Response**:
#     ```json
#     {
#       "status": true,
#       "responseCode": 200,
#       "responseData": {
#         "attached_media": [
#           { "media_fbid": "12332435" },
#           { "media_fbid": "31334242" }
#         ]
#       }
#     }
#     ```

#     **Returns**:
#     - `attached_media` (list): A list of media IDs attached to the post.
# """


#     response = FacebookService.upload_multiple_media(page_id, payload, access_token)
#     return UriResponse.get_status_response(
#         response=response, status_code=response["responseCode"]
#     )
@router.get("/ai-media-report")
async def media_ai_reports(
    cache_key: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await FacebookService.fetch_ai_post_report(db, cache_key)

    return UriResponse.get_status_response(
        response=data, status_code=data["responseCode"]
    )


@router.post("/page/reels")
async def post_reel_video(
    page_id: str, page_access_token: str, payload: FacebookReelVideoPayload
):
    data = await FacebookService.publish_reel_video(page_id, payload, page_access_token)

    return UriResponse.get_status_response(
        response=data, status_code=data["responseCode"]
    )
