from http import HTTPStatus
import requests
from app.core.config import settings
from app.domain.responses.uri_response import UriResponse
from app import schemas
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.InfluencerRepository import InfluencerRepository
from app.domain.enums.tiktok_enum import TiktokMediaTypeEnum
from app.domain.requests.tiktok_requests import PostModel
from app.domain.schemas import influencer_schema
from app.domain.enums.account_enum import AccountTypeEnum


class TiktokService:
    @staticmethod
    async def fetch_hashtag_search(
        keyword: List[str],
        fields: Optional[str] = "id,like_count",
        start_date: Optional[str] = "20220615",
        end_date: Optional[str] = "20220628",
        cursor: Optional[str] = None,
    ):
        url = f"https://open.tiktokapis.com/v2/research/video/query/?fields={fields}"

        body = {
            "query": {
                "and": [
                    {
                        "operation": "EQ",
                        "field_name": "keyword",
                        "field_values": keyword,
                    }
                ]
            },
            "start_date": start_date,
            "end_date": end_date,
            "max_count": 10,
        }

        if cursor:
            body["cursor"] = cursor

        headers = {"Authorization": f"Bearer {settings.TIKTOK_CLIENT_TOKEN}"}

        response = requests.get(url, headers=headers)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "media", None, code=response.status_code
            )

        result = response.json()

        return UriResponse.get_single_data_response("media", result["data"])

    @staticmethod
    async def fetch_discovery(
        username: str,
        access_token: str,
        fields: Optional[str],
    ):
        base_url = "https://open.tiktokapis.com/v2/user/info/"
        full_url = f"{base_url}?fields={fields}"
        params = {"username": username}
        headers = {"Authorization": f"Bearer {access_token}"}

        print("TikTok discovery full URL:", full_url)
        print("TikTok token:", access_token)

        response = requests.get(url=full_url, params=params, headers=headers)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "user", None, code=response.status_code
            )

        result = response.json()
        return UriResponse.get_single_data_response("user", result["data"])

    @staticmethod
    async def fetch_business_discovery(
        username: str, access_token: str, fields: Optional[str]
    ):
        # Fetch business discovery data
        discovery_data = await TiktokService.fetch_discovery(
            username=username, access_token=access_token, fields=fields
        )

        print("Discovery Data : ", discovery_data)

        if discovery_data.get("status") is not True:
            print("Failed to fetch business discovery data")
            return discovery_data  # Return early if discovery fails

        # Fetch media data
        media_data = await TiktokService.fetch_business_media(
            access_token=access_token,
            fields="id,title,video_description,duration,cover_image_url,embed_link",
        )

        # Combine both discovery and media data
        combined_data = {
            **discovery_data.get("responseData").get("user"),
            "media": media_data.get("responseData"),
        }

        return UriResponse.get_single_data_response("business", combined_data)

    @staticmethod
    async def save_tiktok_account(
        user_id: str, username: str, access_token: str, db: AsyncIOMotorDatabase
    ):
        fields = "username,display_name,open_id,union_id,avatar_url_100,avatar_url,avatar_large_url,profile_deep_link,is_verified,bio_description,is_verified,follower_count,following_count,likes_count,video_count"

        discovery = await TiktokService.fetch_discovery(username, access_token, fields)

        print("Discovery : ", discovery)
        if discovery and discovery.get("status"):

            print("Discovery : ", discovery)
            tiktok_user = discovery.get("responseData", {}).get("user", None)

            if tiktok_user:
                influencer_data = influencer_schema.InfluencerCreate(
                    user_id=user_id,
                    social_name=tiktok_user.get("display_name", ""),
                    profile_pic=tiktok_user.get("avatar_url", ""),
                    social_user_id=tiktok_user.get("union_id", ""),
                    social_username=tiktok_user.get("username", ""),
                    social_platform="TIKTOK",
                    account_type=AccountTypeEnum.PERSONAL,
                    connected=True,
                    token=access_token,
                )

                # Perform a create or update operation
                await InfluencerRepository.create_or_update_influencer(
                    db, influencer_data
                )

                influencer_data = (
                    await InfluencerRepository.get_influencers_by_filter(db, user_id)
                ).dict()
                return UriResponse.get_single_data_response(
                    "influencer accounts", influencer_data
                )
            return UriResponse.get_single_data_response("influencer account", None)

        return UriResponse.get_single_data_response("influencer account", None)

    @staticmethod
    async def fetch_business_media(
        access_token: str, fields: Optional[str], next: Optional[str] = None
    ):
        # Base URL and headers setup
        base_url = "https://open.tiktokapis.com/v2/video/list/"
        full_url = f"{base_url}?fields={fields}"
        headers = {"Authorization": f"Bearer {access_token}"}

        print("TikTok media full URL:", full_url)
        print("TikTok token:", access_token)

        # Request to get media list
        response = requests.post(url=full_url, headers=headers)
        print("Media Data : ", response.json())

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "media", None, code=response.status_code
            )

        # Extract media data and video IDs
        result = response.json()

        print("Media Data Result : ", result)
        media_data = result.get("data", {}).get("videos", [])
        video_ids = [media["id"] for media in media_data]

        # Fetch all stats for these video IDs in one API call
        stats_response = await TiktokService.fetch_video_stats(access_token, video_ids)

        print("Stats Result : ", stats_response)
        video_stats = stats_response.get("responseData", {}).get("videos", [])

        # Map stats data by video ID for easy access
        stats_by_id = {stat["id"]: stat for stat in video_stats}

        # Merge stats into media data
        for media in media_data:
            video_id = media.get("id")
            if video_id in stats_by_id:
                media.update(stats_by_id[video_id])

        # Return the combined data with stats included in each media item
        return UriResponse.get_single_data_response("media", media_data)

    @staticmethod
    async def fetch_video_stats(access_token: str, video_ids: List[str]):
        """
        Fetches the stats for a list of videos including likes, comments, shares, etc.
        """
        url = "https://open.tiktokapis.com/v2/video/query/?fields=id,like_count,comment_count,share_count,view_count"
        headers = {"Authorization": f"Bearer {access_token}"}

        # Prepare the payload with the video IDs to fetch stats for
        payload = {"filters": {"video_ids": video_ids}}

        response = requests.post(url, headers=headers, json=payload)

        print("Video Stat Response : ", response)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "video_stats", None, code=response.status_code
            )

        result = response.json()
        return UriResponse.get_single_data_response("video_stats", result.get("data"))

    @staticmethod
    async def fetch_user_demographics(access_token: str, username: str):
        """
        Fetches demographic information for a specified user.
        """
        url = f"https://open.tiktokapis.com/v2/user/info/?fields=age,gender,location,follower_demographics"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"username": username}

        response = requests.get(url, headers=headers, params=params)

        print("Demographics Response : ", response.json())

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "demographics", None, code=response.status_code
            )

        result = response.json()
        return UriResponse.get_single_data_response("demographics", result.get("data"))

    @staticmethod
    async def fetch_video_impressions_and_reach(
        access_token: str, video_ids: List[str]
    ):
        """
        Fetches impression and reach data for a list of videos.
        """
        url = "https://open.tiktokapis.com/v2/video/query/?fields=id,view_count"
        headers = {"Authorization": f"Bearer {access_token}"}

        payload = {"filters": {"video_ids": video_ids}}

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "impressions_and_reach", None, code=response.status_code
            )

        result = response.json()
        return UriResponse.get_single_data_response(
            "impressions_and_reach", result.get("data")
        )

    @staticmethod
    async def fetch_video_comments(access_token: str, video_id: str):
        """
        Fetches comments for a specific video, to be used for sentiment analysis.
        """
        url = f"https://open.tiktokapis.com/v2/video/comments/?video_id={video_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)

        print("Comments Response : ", response.text)
        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "comments", None, code=response.status_code
            )

        result = response.json()
        return UriResponse.get_single_data_response(
            "comments", result.get("data", {}).get("comments", [])
        )

    @staticmethod
    async def initiate_media_upload(access_token: str, post_model: PostModel):
        """
        Initiates a media upload (video or photo) based on the media type within PostModel.
        """
        print("\nPost model: ", post_model)
        url = f"https://open.tiktokapis.com/v2/post/publish/{'video' if post_model.media_type == TiktokMediaTypeEnum.VIDEO else 'content'}/init/"
        print("\nURL: ", url)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        payload = {
            "post_info": post_model.post_info.dict(),
            "source_info": post_model.source_info.dict(),
        }
        if post_model.media_type == TiktokMediaTypeEnum.PHOTO:
            payload.update(
                {"post_mode": "DIRECT_POST", "media_type": TiktokMediaTypeEnum.PHOTO}
            )

        response = requests.post(url, headers=headers, json=payload)
        print(
            "\nResult from posting on tiktok: ",
            response.json(),
            "Token : ",
            access_token,
        )
        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                f"{post_model.media_type} upload", None, code=response.status_code
            )
        print("\nPrint media type: ", post_model.media_type)

        result = response.json()
        return UriResponse.get_single_data_response(
            f"{post_model.media_type} upload", result.get("data")
        )

    @staticmethod
    async def upload_video_from_file(upload_url: str, video_path: str):
        """
        Handles video file upload in chunks to the provided TikTok upload URL.
        """
        with open(video_path, "rb") as video_file:
            video_data = video_file.read()
        headers = {
            "Content-Range": f"bytes 0-{len(video_data)-1}/{len(video_data)}",
            "Content-Type": "video/mp4",
        }
        response = requests.put(upload_url, headers=headers, data=video_data)
        if response.status_code != HTTPStatus.CREATED:
            return UriResponse.update_response("Tiktok video upload", response.json())
        return UriResponse.create_response("Tiktok video upload", True)

    @staticmethod
    async def fetch_post_status(access_token: str, publish_id: str):
        """
        Fetches the status of a media post using the publish ID.
        """
        url = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        payload = {"publish_id": publish_id}

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "post_status", None, code=response.status_code
            )

        result = response.json()
        return UriResponse.get_single_data_response("post_status", result.get("data"))
