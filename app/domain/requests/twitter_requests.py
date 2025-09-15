from pydantic import BaseModel, Field, validator
from typing import List, Optional
from fastapi import Query
from app.domain.enums.twitter_enum import TwitterEnum, MediaCategory


class PaginationParams(BaseModel):
    max_results: Optional[int] = Query(
        100,
        ge=1,
        le=100,
        description="Maximum number of results per page. Defaults to 10.",
    )
    pagination_token: Optional[str] = Query(
        None, description="Token to request the next or previous page of results."
    )


class CurrentUserLookupParams(BaseModel):
    expansions: Optional[str] = Query(
        None,
        description="Comma-separated list of expansions to include in the response.",
    )
    tweet_fields: Optional[str] = Query(
        TwitterEnum.USER_TWEET_FIELDS.value,
        description="Comma-separated list of fields to include in Tweet objects.",
    )
    user_fields: Optional[str] = Query(
        TwitterEnum.AUTH_USER_FIELDS.value,
        description="Comma-separated list of fields to include in User objects.",
    )


class FieldsParams(BaseModel):
    expansions: Optional[str] = Query(
        TwitterEnum.EXPANSIONS.value,
        description="Comma-separated list of expansions to include in the response.",
    )
    tweet_fields: Optional[str] = Query(
        TwitterEnum.TWEET_FIELDS.value,
        description="Comma-separated list of fields to include in Tweet objects.",
    )
    user_fields: Optional[str] = Query(
        TwitterEnum.USER_FIELDS.value,
        description="Comma-separated list of fields to include in User objects.",
    )
    media_fields: Optional[str] = Query(
        TwitterEnum.MEDIA_FIELDS.value,
        description="Comma-separated list of fields to include in Media objects.",
    )
    place_fields: Optional[str] = Query(
        TwitterEnum.PLACE_FIELDS.value,
        description="Comma-separated list of fields to include in Place objects.",
    )
    poll_fields: Optional[str] = Query(
        TwitterEnum.POLL_FIELDS.value,
        description="Comma-separated list of fields to include in Poll objects.",
    )


class TimeRangeParams(BaseModel):
    start_time: Optional[str] = Query(
        None, description="Oldest UTC timestamp for results (ISO 8601)."
    )
    end_time: Optional[str] = Query(
        None, description="Newest UTC timestamp for results (ISO 8601)."
    )


class TwitterSearchRequest(BaseModel):
    query: str = Query(..., description="The search query (required).")
    next_token: Optional[str] = Query(
        None, description="Token to fetch the next page of results."
    )
    page_size: Optional[int] = Query(
        10, description="Number of results per page (defaults to 10)."
    )


class TweetSearchParams(PaginationParams, FieldsParams, TimeRangeParams):
    query: str = Query(..., description="The search query string.")
    since_id: Optional[str] = Query(
        None, description="Return results with Tweet IDs greater than the specified ID."
    )
    until_id: Optional[str] = Query(
        None, description="Return results with Tweet IDs less than the specified ID."
    )
    includes: Optional[List[str]] = Query(
        None, description="Keywords to include in the search."
    )
    excludes: Optional[List[str]] = Query(
        None, description="Keywords to exclude from the search."
    )
    locations: Optional[List[str]] = Query(
        None, description="Locations for site-specific searches."
    )
    hashtags: Optional[List[str]] = Query(
        None, description="Filter tweets containing specific hashtags."
    )
    min_retweets: Optional[int] = Query(
        None, description="Filter tweets with a minimum number of retweets."
    )
    min_likes: Optional[int] = Query(
        None, description="Filter tweets with a minimum number of likes."
    )
    min_replies: Optional[int] = Query(
        None, description="Filter tweets with a minimum number of replies."
    )
    languages: Optional[List[str]] = Query(
        None, description="Filter tweets for specific languages (e.g., 'en', 'es')."
    )
    from_user: Optional[str] = Query(
        None, description="Filter tweets from a specific user."
    )
    to_user: Optional[str] = Query(
        None, description="Filter tweets directed to a specific user."
    )
    is_reply: Optional[bool] = Query(
        None, description="Filter tweets that are replies."
    )
    is_retweet: Optional[bool] = Query(
        None, description="Filter tweets that are retweets."
    )
    sort: Optional[str] = Query(
        "recency", description="Sort order of results ('recency' or 'relevancy')."
    )


class TweetCountsParams(TimeRangeParams):
    query: str = Query(..., description="The search query string.")
    granularity: Optional[str] = Query(
        None,
        description="Granularity for time series data ('minute', 'hour', or 'day').",
    )
    since_id: Optional[str] = Query(
        None, description="Return results with Tweet IDs greater than the specified ID."
    )
    until_id: Optional[str] = Query(
        None, description="Return results with Tweet IDs less than the specified ID."
    )


class TimelineParams(PaginationParams, FieldsParams, TimeRangeParams):
    exclude: Optional[str] = Query(
        None, description="Comma-separated list of exclusions ('retweets', 'replies')."
    )


class LikesParams(PaginationParams, FieldsParams):
    pass


class MentionsParams(PaginationParams, FieldsParams, TimeRangeParams):
    pass


class ListLookupParams(FieldsParams):
    expansions: Optional[str] = Query(
        None, description="Comma-separated list of expansions (e.g., 'owner_id')."
    )


class UserLookupParams(FieldsParams):
    ids: str = Query(..., description="Comma-separated list of User IDs or usernames.")


class FollowsParams(PaginationParams, FieldsParams):
    """
    Parameters for fetching a user's followers or following.
    """

    max_results: Optional[int] = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of results per page. Defaults to 100.",
    )
    user_fields: Optional[str] = Query(
        TwitterEnum.USER_FIELDS.value,
        description="Comma-separated list of user fields to include in returned objects.",
    )


class XLikesParams(PaginationParams, FieldsParams):
    """
    Parameters for fetching users who liked a Tweet.
    """

    tweet_fields: Optional[str] = Query(
        TwitterEnum.TWEET_FIELDS.value,
        description="Comma-separated list of specific fields to include for pinned Tweets.",
    )


class RetweetsParams(PaginationParams, FieldsParams):
    """
    Parameters for fetching retweets of a specific Tweet.
    """

    tweet_fields: Optional[str] = Query(
        TwitterEnum.TWEET_FIELDS.value,
        description="Comma-separated list of specific Tweet fields to include.",
    )


class QuoteTweetsParams(PaginationParams, FieldsParams):
    """
    Parameters for fetching quote tweets for a specific Tweet ID.
    """

    exclude: Optional[str] = Query(
        None,
        description="Comma-separated list of types to exclude ('retweets', 'replies').",
    )


class OwnedListsParams(PaginationParams, FieldsParams):
    """
    Parameters for fetching lists owned by a user.
    """

    list_fields: Optional[str] = Query(
        None,
        description="Comma-separated list of list fields to include (e.g., 'created_at,private').",
    )


class ListTweetsParams(PaginationParams, FieldsParams):
    """
    Parameters for fetching tweets from a list.
    """

    pass


class ListMembersParams(PaginationParams, FieldsParams):
    """
    Parameters for fetching members of a specific list.
    """

    pass


class PinnedListsParams(FieldsParams):
    """
    Parameters for fetching pinned lists of a user.
    """

    list_fields: Optional[str] = Query(
        None,
        description="Comma-separated list of list fields to include (e.g., 'created_at,private').",
    )


class SpaceSearchParams(PaginationParams):
    """
    Parameters for searching Spaces.
    """

    query: str = Query(..., description="The search term for Spaces.")
    space_fields: Optional[str] = Query(
        None,
        description="Comma-separated list of Space fields to include (e.g., 'title,participant_count').",
    )
    topic_fields: Optional[str] = Query(
        None,
        description="Comma-separated list of topic fields to include (e.g., 'id,name').",
    )
    user_fields: Optional[str] = Query(
        TwitterEnum.USER_FIELDS.value,
        description="Comma-separated list of user fields to include in the response.",
    )


class SpaceLookupParams(PaginationParams):
    """
    Parameters for looking up details about specific Spaces.
    """

    ids: str = Query(..., description="Comma-separated list of Space IDs.")
    space_fields: Optional[str] = Query(
        None,
        description="Comma-separated list of Space fields to include (e.g., 'title,state').",
    )


class RetweetedByParams(PaginationParams, FieldsParams):
    """
    Parameters for fetching users who retweeted a specific Tweet.
    """

    pass


class TweetLookupParams(FieldsParams):
    """
    Parameters for looking up details about specific Tweets.
    """

    ids: str = Query(..., description="Comma-separated list of Tweet IDs (required).")


class CreateRetweetPayload(BaseModel):
    """
    Payload for creating a retweet.
    """

    tweet_id: str = Query(
        ..., description="The ID of the Tweet that you would like the user to retweet."
    )


class UsersLookupParams(FieldsParams):
    """
    Parameters for looking up details about specific users.
    """

    ids: str = Query(..., description="Comma-separated list of User IDs or usernames.")


class CreatorSpacesParams(PaginationParams):
    """
    Parameters for fetching Spaces created by a specific user.
    """

    user_ids: str = Query(
        ...,
        description="Comma-separated list of User IDs whose Spaces you want to fetch.",
    )
    space_fields: Optional[str] = Query(
        None,
        description="Comma-separated list of Space fields to include (e.g., 'title,state,participant_count').",
    )
    topic_fields: Optional[str] = Query(
        None,
        description="Comma-separated list of topic fields to include (e.g., 'id,name').",
    )
    user_fields: Optional[str] = Query(
        TwitterEnum.USER_FIELDS.value,
        description="Comma-separated list of user fields to include (e.g., 'username,verified').",
    )


class SpaceBuyersParams(PaginationParams):
    """
    Parameters for fetching users who bought tickets for a specific Space.
    """

    space_id: str = Query(
        ..., description="The ID of the Space for which to fetch ticket buyers."
    )
    user_fields: Optional[str] = Query(
        TwitterEnum.USER_FIELDS.value,
        description="Comma-separated list of user fields to include (e.g., 'username,verified').",
    )
    expansions: Optional[str] = Query(
        None,
        description="Comma-separated list of expansions (e.g., 'pinned_tweet_id').",
    )


class SingleTweetParams(FieldsParams):
    """
    Parameters for fetching details of a single Tweet.
    """

    id: str = Query(
        ..., description="The ID of the Tweet to fetch details for (required)."
    )


class LikedTweetsParams(PaginationParams, FieldsParams):
    """
    Parameters for fetching Tweets liked by a user.
    """

    user_id: str = Query(
        ..., description="The ID of the user whose liked Tweets you want to retrieve."
    )
    expansions: Optional[str] = Query(
        None,
        description="Comma-separated list of expansions (e.g., 'attachments.media_keys,author_id').",
    )


class Geo(BaseModel):
    place_id: Optional[str]


class Media(BaseModel):
    media_ids: Optional[List[str]]
    tagged_user_ids: Optional[List[str]]


class Poll(BaseModel):
    options: List[str]
    duration_minutes: int


class Reply(BaseModel):
    in_reply_to_tweet_id: Optional[str]
    exclude_reply_user_ids: Optional[List[str]]


class CreateTweetPayload(BaseModel):
    text: Optional[str] = None
    direct_message_deep_link: Optional[str] = None
    for_super_followers_only: Optional[bool] = False
    geo: Optional[Geo] = None
    media: Optional[Media] = None
    poll: Optional[Poll] = None
    quote_tweet_id: Optional[str] = None
    reply: Optional[Reply] = None
    reply_settings: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hello World!",
                "direct_message_deep_link": "https://twitter.com/messages/compose?recipient_id=2244994945",
                "for_super_followers_only": True,
                "geo": {"place_id": "5a110d312052166f"},
                "media": {
                    "media_ids": ["1455952740635586573"],
                    "tagged_user_ids": ["2244994945", "6253282"],
                },
                "poll": {"options": ["Yes", "Maybe", "No"], "duration_minutes": 120},
                "quote_tweet_id": "1455953449422516226",
                "reply": {
                    "in_reply_to_tweet_id": "1455953449422516226",
                    "exclude_reply_user_ids": ["6253282"],
                },
                "reply_settings": "mentionedUsers",
            }
        }


class TwitterSocialMediaPostSettings(BaseModel):
    direct_message_deep_link: Optional[str] = None
    for_super_followers_only: Optional[bool] = False
    geo: Optional[Geo] = None
    media: Optional[Media] = None
    poll: Optional[Poll] = None
    quote_tweet_id: Optional[str] = None
    reply: Optional[Reply] = None
    reply_settings: Optional[str] = None


class MediaInitPayload(BaseModel):
    command: str = Field("INIT", Literal=True)
    total_bytes: int = Field(
        ..., gt=0, description="The size of the media being uploaded in bytes."
    )
    media_type: str = Field(
        ..., description="The MIME type of the media being uploaded."
    )
    media_category: Optional[MediaCategory] = Field(
        None, description="Identifies the media use case for specific constraints."
    )
    additional_owners: Optional[List[int]] = Field(
        None, description="List of user IDs allowed to use the media_id."
    )


class MediaAppendPayload(BaseModel):
    command: str = Field("APPEND", Literal=True)
    media_id: str = Field(
        ..., description="The media_id returned from the INIT command."
    )
    segment_index: int = Field(
        ..., ge=0, le=999, description="Index of the file chunk being uploaded."
    )
    media: Optional[bytes] = Field(
        None, description="The raw binary file content of the chunk."
    )
    media_data: Optional[str] = Field(
        None,
        description="Base64-encoded content of the chunk, used as an alternative to raw binary.",
    )

    @validator("media", always=True)
    def validate_media_or_media_data(cls, media, values):
        if not media and not values.get("media_data"):
            raise ValueError("Either 'media' or 'media_data' must be provided.")
        if media and values.get("media_data"):
            raise ValueError("'media' and 'media_data' cannot both be provided.")
        return media


class MediaFinalizePayload(BaseModel):
    command: str = Field("FINALIZE", Literal=True)
    media_id: str = Field(
        ..., description="The media_id returned from the INIT command."
    )


class MediaStatusPayload(BaseModel):
    command: str = Field("STATUS", Literal=True)
    media_id: str = Field(
        ..., description="The media_id returned from the INIT command."
    )


class MediaMetadataPayload(BaseModel):
    media_id: str = Field(
        ..., description="The media_id returned from the INIT command."
    )
    alt_text: Optional[dict[str, str]] = Field(
        None, description="Additional metadata for the media, such as image alt text."
    )


class MediaSubtitlesDeletePayload(BaseModel):
    media_id: str = Field(..., description="The media_id of the associated video.")
    media_category: MediaCategory = Field(
        ..., description="The media category of the associated video."
    )
    subtitle_info: dict[str, List[dict[str, str]]] = Field(
        ..., description="Details of subtitles to delete, including language codes."
    )
