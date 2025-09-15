from datetime import datetime
import time
from typing import Union
from app.core.helpers.file_helper import FileHelper
from app.domain.requests.facebook_requests import (
    FacebookMultipleMediaPayload,
    FacebookPhotoPayload,
    FacebookPostPayload,
    FacebookVideoPayload,
    FacebookReelVideoPayload,
)


class FacebookHelper:
    @staticmethod
    def construct_post_payload_from_dict(payload: dict, media_payload):
        """
        Creates an instance of FacebookPostPayload from a dictionary.
        Ensures attached_media contains only media_fbid values.
        """
        # Handle `media_payload` as either a dictionary or an object
        if hasattr(media_payload, "attached_media"):
            attached_media = media_payload.attached_media
        elif isinstance(media_payload, dict):
            attached_media = media_payload.get("attached_media", [])
        else:
            attached_media = []

        # Extract only `media_fbid` from attached_media
        if attached_media and isinstance(attached_media, list):
            attached_media = [
                {"media_fbid": item.get("media_fbid")}
                for item in attached_media
                if isinstance(item, dict) and "media_fbid" in item
            ]

        result_dict = {
            "message": payload.get("content"),
            "published": True,
            # "scheduled_publish_time": payload.get("start_time"),
            "attached_media": attached_media,
        }
        print("Result Dict : ", result_dict)
        return result_dict

    @staticmethod
    def construct_scheduled_post_payload_from_dict(
        payload: dict,
    ) -> FacebookPostPayload:
        """
        Creates an instance of FacebookPostPayload from a dictionary
        :param payload: Dictionary containing the post data
        :Returns: An instance of FacebookPostPayload
        """
        post_date = payload.get("start_date", None)
        post_time = payload.get("start_time", None)

        if isinstance(post_date, str):
            payload["start_date"] = datetime.strptime(
                post_date, "%Y-%m-%dT%H:%M:%S.%fZ"
            ).date()
        if isinstance(post_time, str):
            payload["start_time"] = datetime.fromisoformat(
                post_time.replace("Z", "")
            ).time()
        result_dict = {
            "message": payload["content"],
            "link": payload["post_url"],
            "published": False,
            "scheduled_publish_time": FacebookHelper.get_unix_timestamp_from_date_time(
                payload["start_date"], payload["start_time"]
            ),
            # "targeting": post_settings.get("targeting") if post_settings else {},
        }
        result_payload = FacebookPostPayload(**result_dict)
        return result_payload

    @staticmethod
    def get_unix_timestamp_from_date_time(start_date, start_time):
        """
        Transforms a date-time object to a unix timestamp
        :param start_date: Scheduled day
        :param start_time: Scheduled time
        :Returns: A UNIX timestamp
        """
        if start_date and start_time:
            date_time = datetime.combine(start_date, start_time)
            unix_timestamp = time.mktime(date_time.timetuple())
            return unix_timestamp
        return None

    @staticmethod
    def construct_photo_post_payload_from_dict(
        payload: dict,
    ) -> Union[FacebookPhotoPayload, FacebookMultipleMediaPayload]:
        """
        Creates an instance of FacebookPhotoPayload from a dictionary
        :param payload: Dictionary containing the post data
        :Returns: An instance of FacebookPhotoPayload
        """
        if len(payload["media"]) == 1:
            result_dict = {
                "url": payload["media"][0]["url"],
                "caption": payload["media"][0]["caption"],
            }
            result_payload = FacebookPhotoPayload(**result_dict)
        elif len(payload["media"]) > 1:
            result_dict = FacebookHelper.construct_post_payload_from_dict(
                payload, payload["media"]
            ).dict()
            result_dict["attached_media"] = [
                FacebookPhotoPayload(
                    url=media_item.get("url", None),
                    caption=media_item.get("caption", None),
                ).dict()
                for media_item in payload.get("media", None)
            ]
            result_payload = FacebookMultipleMediaPayload(**result_dict)
        else:
            raise ValueError("No media items were inputted")
        return result_payload

    @staticmethod
    def construct_video_post_payload_from_dict(payload: dict):
        """
        Creates an instance of FacebookPhotoPayload from a dictionary
        :param payload: Dictionary containing the post data
        :Returns: An instance of FacebookPhotoPayload
        """
        post_settings = payload.get("settings", None)
        media_url = payload["media"][0]["url"]
        result_dict = {
            "title": (
                post_settings.get("title") if post_settings else payload["content"]
            ),
            "description": (
                post_settings.get("description")
                if post_settings
                else payload["media"][0]["caption"]
            ),
            "video_url": media_url,
            "file_data": (
                post_settings.get("file_data")
                if post_settings
                else {
                    "file_name": "video.mp4",
                    "file_length": FileHelper.get_file_size(media_url),
                    "file_type": "video/mp4",
                }
            ),
        }
        result_payload = FacebookVideoPayload(**result_dict)
        return result_payload

    @staticmethod
    async def extract_data_for_ai_post_insights(data: dict) -> dict:
        # Extract post data
        post_data = data.get("post_data", [])
        posts = []

        for post in post_data:
            # Extract the first attachment safely
            attachments = post.get("attachments", {}).get("data", [])
            first_attachment = attachments[0] if attachments else {}

            transformed_post = {
                "media": {
                    "media_type": first_attachment.get("media_type", "unknown"),
                    "caption": first_attachment.get("description", "No caption"),
                },
                "timestamp": post.get("created_time"),
                "engagement": {
                    "reactions": post.get("reactions", {})
                    .get("summary", {})
                    .get("total_count", 0),
                },
            }
            posts.append(transformed_post)

        # Construct the transformed JSON
        transformed_json = {"posts": posts}

        return transformed_json

    @staticmethod
    def construct_reel_video_payload(payload: dict) -> FacebookReelVideoPayload:
        media_data = payload.get("media", [])
        video_url = media_data[0].get("url", None)
        description = payload.get("content", None)
        if not video_url or not description:
            raise ValueError("Video url or description not found")
        result_dict = {"video_url": video_url, "description": description}
        result_payload = FacebookReelVideoPayload(**result_dict)
        return result_payload
