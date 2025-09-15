from typing import Dict, Any
from http import HTTPStatus
import requests
from fastapi import HTTPException
from app.domain.responses.uri_response import UriResponse
from app.domain.requests.twitter_requests import CreateTweetPayload


class XManageTweetService:
    """
    Service for managing Tweets via the X API.
    Provides methods to:
    - Create a Tweet on behalf of an authenticated user
    - Delete a Tweet
    """

    BASE_URL = "https://api.x.com/2/tweets"

    @staticmethod
    async def create_tweet(
        access_token: str, payload: CreateTweetPayload
    ) -> Dict[str, Any]:
        """
        Creates a Tweet on behalf of an authenticated user.

        :param access_token: Bearer token for authentication.
        :param payload: JSON payload containing Tweet creation details.
        :return: JSON response containing the created Tweet details.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Make API request
        response = requests.post(
            XManageTweetService.BASE_URL, headers=headers, json=payload
        )

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to create Tweet."),
            )

        return UriResponse.get_single_data_response("tweet", response.json())

    @staticmethod
    def delete_tweet(access_token: str, tweet_id: str) -> Dict[str, Any]:
        """
        Deletes a Tweet by ID.

        :param access_token: Bearer token for authentication.
        :param tweet_id: The ID of the Tweet to be deleted.
        :return: JSON response indicating the delete operation's success.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Make API request
        response = requests.delete(
            f"{XManageTweetService.BASE_URL}/{tweet_id}", headers=headers
        )

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to delete Tweet."),
            )

        return UriResponse.get_single_data_response("deleted", response.json())
