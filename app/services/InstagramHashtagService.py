from collections import Counter
from http import HTTPStatus
import requests
from app.core.config import settings
from app.core.helpers.text_helper import TextHelper
from app.domain.responses.uri_response import UriResponse
from app import schemas
from typing import Any, Collection, List, Optional, Dict
from fastapi import HTTPException
from app.repository.HashtagRepository import HashtagRepository


class InstagramHashtagService:
    # --- Private Helpers ---
    @staticmethod
    def _sort_media_by_timestamp(media: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(media, key=lambda x: x.get("timestamp", ""), reverse=True)

    # --- Public Methods ---
    @staticmethod
    async def track_hashtag(
        hashtag: str,
        db: Collection,
        access_token: Optional[str] = None,
        instagram_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tracks a hashtag by checking the database first, then fetching from Meta API if necessary."""
        hashtag_normalized = hashtag.lower()

        response = await InstagramHashtagService.fetch_instagram_hashtag_id(
            hashtag_normalized, db, access_token, instagram_user_id
        )

        instagram_hashtag_id: Optional[str] = None
        if response["status"] is True:
            instagram_hashtag_id = response.get("responseData")

        if instagram_hashtag_id:
            media_response = (
                await InstagramHashtagService.fetch_hashtag_media(
                    instagram_hashtag_id,
                    access_token=access_token,
                    instagram_user_id=instagram_user_id,
                )
            ).get("responseData", {})

            media_response["media"] = InstagramHashtagService._sort_media_by_timestamp(
                media_response.get("media", [])
            )

            post_type_distribution = Counter(
                media["media_type"] for media in media_response["media"]
            )

            media_response["post_type_distribution"] = [
                {"media_type": key, "count": value}
                for key, value in post_type_distribution.items()
            ]

            media_response["hashtag_mention_frequency"] = (
                TextHelper.compute_hashtag_frequency(media_response["media"], "caption")
            )

            return UriResponse.get_single_data_response(
                f"{hashtag} data", media_response
            )
        return UriResponse.get_single_data_response("hashtag", None)

    @staticmethod
    async def fetch_instagram_hashtag_id(
        hashtag: str,
        db: Collection,
        access_token: Optional[str] = None,
        instagram_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetches the Instagram hashtag ID for a given keyword and saves it to the database if it's not already saved."""

        # Normalize keyword
        keyword = hashtag.lower()

        # 1. Check cache / DB
        existing = await HashtagRepository.get_hashtag_by_word(db, keyword)
        if existing:
            return UriResponse.get_single_data_response(
                "hashtag id", existing["instagram_hashtag_id"]
            )

        # 2. Prepare tokens & user ID
        default_token = settings.META_SYSTEM_TOKEN
        default_instagram_user_id = settings.INSTAGRAM_BUSINESS_ID
        token = access_token or default_token
        instagram_user_id = instagram_user_id or default_instagram_user_id

        # 3. Helper to build URL and perform request
        def _fetch(token_to_use: str, instagram_id: str) -> requests.Response:
            url = (
                f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}"
                f"/ig_hashtag_search"
                f"?q={hashtag}"
                f"&user_id={instagram_id}"
                f"&access_token={token_to_use}"
            )
            return requests.get(url)

        # 4. Try initial request
        response = _fetch(token, instagram_user_id)
        # 5. Retry once with default token if unauthorized/forbidden on a non-default
        if (
            response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN)
            and token != default_token
        ):
            print("Refetching with default arguments.....")
            response = _fetch(default_token, default_instagram_user_id)

        # 6. Handle errors
        if response.status_code != HTTPStatus.OK:
            detail = {}
            try:
                detail = response.json()
            except ValueError:
                detail = {"message": "Failed to parse error response"}
            raise HTTPException(status_code=response.status_code, detail=detail)

        # 7. Parse and validate payload
        data = response.json().get("data", [])
        if not data:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"No hashtag '{hashtag}' found on Instagram",
            )

        hashtag_id = data[0]["id"]

        # 8. Persist and return
        new_record = schemas.HashtagCreate(
            keyword=keyword, instagram_hashtag_id=hashtag_id
        )
        await HashtagRepository.create_hashtag(db, new_record)

        return UriResponse.get_single_data_response("hashtag id", hashtag_id)

    # @staticmethod
    # def fetch_hashtag_media(
    #     instagram_hashtag_id: str,
    #     media_type: str = "top_media",  # Accepts either 'top_media' or 'recent_media'
    #     access_token: Optional[str] = None,
    #     fields: Optional[str] = None,
    #     before: Optional[str] = None,
    #     after: Optional[str] = None,
    #     limit: int = 100,  # Total number of posts to fetch
    # ) -> Dict[str, Any]:
    #     """Fetches up to `limit` media posts associated with a hashtag, supporting pagination."""
    #     if not access_token:
    #         access_token = settings.META_SYSTEM_TOKEN  # Use your app's system token

    #     # All possible fields we want to retrieve
    #     if not fields:
    #         fields = "id,media_type,media_url,permalink,timestamp,comments_count,like_count,caption,children{media_url,media_type,permalink}"

    #     # Initialize variables for collecting media data
    #     all_media: list = InstagramHashtagService.fetch_recent_media(
    #         instagram_hashtag_id, access_token, fields
    #     )

    #     next_page_cursor = after

    #     # Fetch media data until the limit is reached
    #     while len(all_media) < limit:
    #         # Construct the URL for the API request
    #         url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{instagram_hashtag_id}/{media_type}?user_id={settings.INSTAGRAM_BUSINESS_ID}&fields={fields}&access_token={access_token}"

    #         if next_page_cursor:
    #             url += f"&after={next_page_cursor}"
    #         elif before:
    #             url += f"&before={before}"

    #         # Make the API request
    #         response = requests.get(url)
    #         print("Hashtag Media Response: ", response.json())

    #         if response.status_code != HTTPStatus.OK:
    #             raise HTTPException(
    #                 status_code=response.status_code, detail=response.json()
    #             )

    #         # Parse the response
    #         media_data = response.json()
    #         all_media.extend(media_data.get("data", []))  # Add new media to the list

    #         # Check for pagination and update the cursor
    #         pagination = media_data.get("paging", {})
    #         next_page_cursor = pagination.get("cursors", {}).get("after")

    #         # Break the loop if there are no more pages
    #         if not next_page_cursor:
    #             break

    #     # Slice the media to the limit, in case the API returns more than needed in the last request
    #     all_media = all_media[:limit]

    #     # Return the collected media data
    #     return UriResponse.get_single_data_response(
    #         "hashtag media", {"media": all_media, "count": len(all_media)}
    #     )

    @staticmethod
    async def fetch_hashtag_media(
        instagram_hashtag_id: str,
        instagram_user_id: Optional[str] = None,
        access_token: Optional[str] = None,
        fields: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 100,  # Total number of posts to fetch
    ) -> Dict[str, Any]:
        """Fetches up to `limit` media posts associated with a hashtag, ensuring recent media is prioritized before filling with top media."""

        if not access_token:
            access_token = settings.META_SYSTEM_TOKEN  # Use your app's system token

        default_instagram_user_id = settings.INSTAGRAM_BUSINESS_ID
        instagram_user_id = instagram_user_id or default_instagram_user_id

        if not fields:
            fields = "id,media_type,media_url,permalink,timestamp,comments_count,like_count,caption,children{media_url,media_type,permalink}"

        # Initialize media collection
        all_media: List[Dict[str, Any]] = []

        # Step 1: Fetch Recent Media first
        try:
            recent_media = await InstagramHashtagService.fetch_recent_media(
                instagram_hashtag_id, instagram_user_id, access_token, fields
            )
            all_media.extend(recent_media)
        except HTTPException as e:
            print(f"HTTPException fetching recent media: {e}")
        except Exception as e:
            print(f"Error fetching recent media: {e}")

        # Step 2: If we have less than `limit`, fetch Top Media to fill up
        if len(all_media) < limit:
            try:
                top_media = await InstagramHashtagService.fetch_top_media(
                    instagram_hashtag_id,
                    instagram_user_id,
                    access_token,
                    fields,
                    limit - len(all_media),
                )
                all_media.extend(top_media)
            except HTTPException as e:
                print(f"HTTPException fetching recent media: {e}")
            except Exception as e:
                print(f"Error fetching recent media: {e}")

        # Remove duplicates (ensure unique media by ID)
        unique_media = {media["id"]: media for media in all_media}.values()

        # Slice to enforce the limit
        final_media = list(unique_media)[:limit]

        return UriResponse.get_single_data_response(
            "hashtag media", {"media": final_media, "count": len(final_media)}
        )

    @staticmethod
    async def fetch_recent_media(
        instagram_hashtag_id: str,
        instagram_user_id: str,
        access_token: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetches recent media posts associated with a hashtag. No pagination."""

        if not access_token:
            access_token = settings.META_SYSTEM_TOKEN  # Use your app's system token

        if not fields:
            fields = "id,media_type,media_url,permalink,timestamp,comments_count,like_count,caption,children{media_url,media_type,permalink}"

        url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{instagram_hashtag_id}/recent_media?user_id={instagram_user_id}&fields={fields}&access_token={access_token}"

        response = requests.get(url)
        print("Recent Media Response: ", response.json())

        if response.status_code == HTTPStatus.OK:
            return response.json().get("data", [])

        raise HTTPException(status_code=response.status_code, detail=response.json())

    @staticmethod
    async def fetch_top_media(
        instagram_hashtag_id: str,
        instagram_user_id: str,
        access_token: Optional[str] = None,
        fields: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetches top media posts associated with a hashtag, using pagination if needed."""

        if not access_token:
            access_token = settings.META_SYSTEM_TOKEN  # Use your app's system token

        if not fields:
            fields = "id,media_type,media_url,permalink,timestamp,comments_count,like_count,caption,children{media_url,media_type,permalink}"

        all_media: list = []
        next_page_cursor = None

        while len(all_media) < limit:
            url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{instagram_hashtag_id}/top_media?user_id={instagram_user_id}&fields={fields}&access_token={access_token}"

            if next_page_cursor:
                url += f"&after={next_page_cursor}"

            response = requests.get(url)
            print("Top Media Response: ", response.json())

            if response.status_code != HTTPStatus.OK:
                raise HTTPException(
                    status_code=response.status_code, detail=response.json()
                )

            media_data = response.json()
            all_media.extend(media_data.get("data", []))

            pagination = media_data.get("paging", {})
            next_page_cursor = pagination.get("cursors", {}).get("after")

            if not next_page_cursor:
                break

        return all_media[:limit]
