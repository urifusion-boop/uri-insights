from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.domain.responses.uri_response import UriResponse
from app.services.XTweetSearchService import XTweetSearchService
from app.services.XTweetCountService import XTweetCountService
from app.services.XTimelineService import XTimelineService
from app.services.XLikesService import XLikesService
from app.services.TweetLookupService import TweetLookupService
from app.services.XFollowsService import XFollowsService
from app.services.XUsersLookupService import XUsersLookupService
from app.services.XSpacesLookupService import XSpacesLookupService
from app.services.XReTweetService import XReTweetService
from app.services.XQuoteTweetService import XQuoteTweetService
from app.services.XManageTweetService import XManageTweetService
from app.services.XListService import XListService
from app.services.TwitterService import TwitterService
from app.domain.responses.uri_response import UriResponse
from app.core.auth_handler import get_x_access_token
from fastapi.encoders import jsonable_encoder
from app.domain.requests.twitter_requests import (
    TimelineParams,
    TweetSearchParams,
    MentionsParams,
    LikesParams,
    LikedTweetsParams,
    TweetCountsParams,
    TweetLookupParams,
    SingleTweetParams,
    FollowsParams,
    UsersLookupParams,
    SpaceSearchParams,
    SpaceLookupParams,
    CreatorSpacesParams,
    SpaceBuyersParams,
    RetweetedByParams,
    RetweetsParams,
    CreateRetweetPayload,
    QuoteTweetsParams,
    ListLookupParams,
    ListMembersParams,
    ListTweetsParams,
    OwnedListsParams,
    PinnedListsParams,
    CurrentUserLookupParams,
    CreateTweetPayload,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency

router = APIRouter()


@router.get("/tweets/search")
async def search_all_tweets(
    access_token: str = Depends(get_x_access_token),
    params: TweetSearchParams = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Perform a full-archive search for tweets using the X API.

    The request body must include all the necessary parameters as defined in the TweetSearchParams model.
    """
    response = await XTweetSearchService.search_all_tweets(db, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/tweets/recent/search")
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


@router.get("/user/tweets")
async def get_user_tweets(
    social_user_id: str = Query(
        ..., description="The Twitter ID of the user whose tweets are being fetched."
    ),
    access_token: str = Depends(get_x_access_token),
    next: Optional[str] = Query(None, description="The next page token"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch tweets composed by a specific user using the X Timelines API.
    """
    response = await TwitterService.get_user_tweets(
        db, social_user_id, access_token, next
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/user/mentions")
async def get_user_mentions(
    social_user_id: str = Query(
        ..., description="The Twitter ID of the user whose mentions are being fetched."
    ),
    access_token: str = Depends(get_x_access_token),
    next: Optional[str] = Query(None, description="The next page token"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch tweets mentioning a specific user using the Mentions API.
    """
    response = await TwitterService.get_user_mentions(
        db, social_user_id, access_token, next
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/user/timelines/reverse_chronological")
async def get_reverse_chronological_timeline(
    social_user_id: str = Query(
        ...,
        description="The ID of the user requesting their reverse chronological timeline.",
    ),
    start_time: Optional[str] = Query(
        None, description="The start time for filtering tweets (ISO 8601 format)."
    ),
    end_time: Optional[str] = Query(
        None, description="The end time for filtering tweets (ISO 8601 format)."
    ),
    next: Optional[str] = Query(
        None, description="The token for fetching the next page of results."
    ),
    exclude: Optional[str] = Query(
        None,
        description="Exclude specific types of tweets (e.g., 'replies', 'retweets').",
    ),
    access_token: str = Depends(get_x_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch a user's reverse chronological timeline using the Twitter API.

    Args:
        social_user_id (str): The ID of the user whose timeline is being requested.
        start_time (Optional[str]): The start time for filtering tweets (ISO 8601 format).
        end_time (Optional[str]): The end time for filtering tweets (ISO 8601 format).
        next (Optional[str]): The token for fetching the next page of results.
        exclude (Optional[str]): Types of tweets to exclude (e.g., 'replies', 'retweets').
        access_token (str): The access token for authenticating the Twitter API request.
        db (AsyncIOMotorDatabase): AsyncIOMotorDatabase dependency for caching and logging.

    Returns:
        JSON response containing the user's reverse chronological timeline.
    """

    response = await TwitterService.get_reverse_chronological_timeline(
        db, social_user_id, access_token, start_time, end_time, next, exclude
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/tweet/liking_users")
async def get_liking_users(
    tweet_id: str = Query(
        ..., description="The ID of the Tweet whose liking users are being fetched."
    ),
    access_token: str = Depends(get_x_access_token),
    params: LikesParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch users who liked a specific Tweet using the Liking Users API.
    """
    response = await XLikesService.get_liking_users(db, tweet_id, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/user/liked_tweets")
async def get_user_liked_tweets(
    user_id: str = Query(
        ..., description="The ID of the user whose liked Tweets are being fetched."
    ),
    access_token: str = Depends(get_x_access_token),
    params: LikedTweetsParams = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch Tweets liked by a specific user using the Liked Tweets API.
    """
    response = await XLikesService.get_user_liked_tweets(
        db, user_id, params, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/tweets/counts/all")
async def get_tweet_counts(
    access_token: str = Depends(get_x_access_token),
    params: TweetCountsParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch full-archive Tweet counts matching the query using the Tweet Counts API.
    """
    response = await XTweetCountService.get_tweet_counts(db, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/tweets/counts/recent")
async def get_recent_tweet_counts(
    access_token: str = Depends(get_x_access_token),
    params: TweetCountsParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch recent Tweet counts (from the past 7 days) using the recent Tweet counts API.
    """
    response = await XTweetCountService.get_recent_tweet_counts(
        db, params, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/tweets")
async def get_tweets(
    access_token: str = Depends(get_x_access_token),
    params: TweetLookupParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch details for one or more Tweets by their IDs using the Tweet Lookup API.
    """
    response = await TweetLookupService.get_tweets(db, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/tweets/{tweet_id}")
async def get_tweet_by_id(
    tweet_id: str,
    access_token: str = Depends(get_x_access_token),
    params: Optional[SingleTweetParams] = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch details for a single Tweet by its ID using the Tweet Lookup API.
    """
    response = await TweetLookupService.get_tweet_by_id(
        db, tweet_id, params, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/users/{user_id}/followers")
async def get_followers(
    user_id: str,
    access_token: str = Depends(get_x_access_token),
    params: FollowsParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch followers of a specified user.
    """
    response = await XFollowsService.get_followers(db, user_id, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/users/{user_id}/following")
async def get_following(
    user_id: str,
    access_token: str = Depends(get_x_access_token),
    params: FollowsParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch users followed by a specified user.
    """
    response = await XFollowsService.get_following(db, user_id, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/users")
async def get_users_by_ids(
    ids: str,
    access_token: str = Depends(get_x_access_token),
    params: UsersLookupParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch user details for a list of IDs.
    """
    response = await XUsersLookupService.get_users_by_ids(db, ids, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: str,
    access_token: str = Depends(get_x_access_token),
    params: UsersLookupParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch user details for a single user ID.
    """
    response = await XUsersLookupService.get_user_by_id(
        db, user_id, params, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/users/by/username/{username}")
async def get_user_by_username(
    username: str,
    access_token: str = Depends(get_x_access_token),
    params: UsersLookupParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch user details by username.
    """
    response = await XUsersLookupService.get_user_by_username(
        db, username, params, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/user/me")
async def get_current_user(
    access_token: str = Depends(get_x_access_token),
    params: CurrentUserLookupParams = Depends(),
):
    """
    Fetch the currently authenticated user's details.
    """
    response = XUsersLookupService.get_current_user(access_token, params)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/users/by")
async def get_users_by_usernames(
    usernames: str,
    access_token: str = Depends(get_x_access_token),
    params: UsersLookupParams = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch user details for a list of usernames.
    """
    response = await XUsersLookupService.get_users_by_usernames(
        db, usernames, params, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/spaces/search")
async def search_spaces(
    params: SpaceSearchParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    response = await XSpacesLookupService.search_spaces(db, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/spaces")
async def lookup_spaces(
    params: SpaceLookupParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    response = await XSpacesLookupService.lookup_spaces(db, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/spaces/by/creator_ids")
async def lookup_spaces_by_creators(
    params: CreatorSpacesParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    response = await XSpacesLookupService.lookup_spaces_by_creators(
        db, params, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/spaces/{space_id}/buyers")
async def get_space_buyers(
    space_id: str,
    params: SpaceBuyersParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    response = await XSpacesLookupService.get_space_buyers(
        db, space_id, params, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/tweets/{tweet_id}/retweeted_by", tags=["Retweets"])
async def get_retweeted_by(
    tweet_id: str,
    params: RetweetedByParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    """
    Get users who retweeted a specific Tweet.

    - **tweet_id**: ID of the Tweet.
    - **params**: Query parameters for filtering results.
    """
    response = await XReTweetService.get_retweeted_by(
        db, tweet_id, params.dict(exclude_none=True), access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/user/retweets/create", tags=["Retweets"])
async def create_retweet(
    user_id: str,
    payload: CreateRetweetPayload,
    access_token=Depends(get_x_access_token),
):
    """
    Create a retweet on behalf of the authenticated user.

    - **user_id**: ID of the user retweeting the Tweet.
    - **payload**: JSON payload containing the Tweet ID.
    """
    response = XReTweetService.create_retweet(user_id, payload, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/retweets", tags=["Retweets"])
async def get_retweets(
    tweet_id: str,
    params: RetweetsParams = Query(None),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    """
    Get retweets for a specific Tweet ID.

    - **tweet_id**: ID of the Tweet.
    - **params**: Query parameters for filtering results.
    """
    response = await XReTweetService.get_retweets(
        db, tweet_id, params.dict(exclude_none=True), access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/tweets/quote_tweets", tags=["Quote Tweets"])
async def get_quote_tweets(
    tweet_id: str,
    params: QuoteTweetsParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    """
    Get Quote Tweets for a specific Tweet.

    - **tweet_id**: ID of the Tweet.
    - **params**: Query parameters for filtering results.
    """
    response = await XQuoteTweetService.get_quote_tweets(
        db, tweet_id, params, access_token
    )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/lists/{list_id}", tags=["Lists"])
async def get_list_by_id(
    list_id: str,
    params: ListLookupParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    """
    Fetch details of a specific list by ID.
    """
    response = await XListService.get_list_by_id(db, list_id, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/users/{user_id}/owned_lists", tags=["Lists"])
async def get_owned_lists(
    user_id: str,
    params: OwnedListsParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    """
    Fetch lists owned by a specific user.
    """
    response = await XListService.get_owned_lists(db, user_id, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/lists/{list_id}/tweets", tags=["Lists"])
async def get_list_tweets(
    list_id: str,
    params: ListTweetsParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    """
    Fetch tweets from a specific list.
    """
    response = await XListService.get_list_tweets(db, list_id, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/lists/{list_id}/members", tags=["Lists"])
async def get_list_members(
    list_id: str,
    params: ListMembersParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    """
    Fetch members of a specific list.
    """
    response = await XListService.get_list_members(db, list_id, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/users/{user_id}/pinned_lists", tags=["Lists"])
async def get_pinned_lists(
    user_id: str,
    params: PinnedListsParams = Depends(),
    db=Depends(get_db_dependency),
    access_token=Depends(get_x_access_token),
):
    """
    Fetch pinned lists of a specific user.

    - **user_id**: ID of the user whose pinned lists are being fetched.
    - **params**: Query parameters for filtering results.
    """
    response = await XListService.get_pinned_lists(db, user_id, params, access_token)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/user/tweet/create", tags=["Tweets"])
async def create_tweet(
    payload: CreateTweetPayload,
    access_token=Depends(get_x_access_token),
):
    """
    Create a tweet on behalf of the authenticated user.

    - **payload**: JSON payload containing the Tweet ID.
    - **access_token**: Access Token of the user creating the Tweet.
    """
    response = await XManageTweetService.create_tweet(access_token, payload)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/user/tweet/delete", tags=["Tweets"])
async def delete_tweet(
    tweet_id: str,
    access_token=Depends(get_x_access_token),
):
    """
    Deletes a tweet on behalf of the authenticated user.

    - **tweet_id**: The Tweet ID.
    - **access_token**: Access Token of the user deleting the Tweet.
    """
    response = XManageTweetService.delete_tweet(access_token, tweet_id)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/save-twitter-account")
async def save_twitter_account(
    user_id: str,
    x_access_token: str = Depends(get_x_access_token),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = TwitterService.save_twitter_account(db, user_id, x_access_token)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/business-discovery")
async def x_business_discovery(
    db=Depends(get_db_dependency),
    x_access_token: str = Depends(get_x_access_token),
):
    response = await XUsersLookupService.fetch_business_discovery(db, x_access_token)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
