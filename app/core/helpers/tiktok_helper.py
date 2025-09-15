from typing import Any
from app.domain.enums.tiktok_enum import SourceTypeEnum
from app.domain.requests.tiktok_requests import PostModel


class TiktokHelper:
    @staticmethod
    def construct_payload_from_dict(post_data: dict) -> PostModel:
        post_settings: dict[str, Any] = post_data.get("settings", None)

        # Define the payload with explicit typing
        payload: dict[str, Any] = {
            "post_info": {
                "title": post_data["content"],
                "privacy_level": post_settings.get("privacy_level") if post_settings else "SELF_ONLY",
                "disable_duet": post_settings.get("disable_duet") if post_settings else None,
                "disable_comment": post_settings.get("disable_comment") if post_settings else None,
                "disable_stitch": post_settings.get("disable_stitch") if post_settings else None,
                "video_cover_timestamp_ms": post_settings.get(
                    "video_cover_timestamp_ms"
                ) if post_settings else None,
                "description": post_settings.get("description") if post_settings else None,
                "auto_add_music": post_settings.get("auto_add_music") if post_settings else None,
            },
            "source_info": {
                "source": SourceTypeEnum.PULL_FROM_URL,
                "video_size": None,
                "chunk_size": None,
                "total_chunk_count": None,
                "video_url": (
                    post_data["media"][0]["url"]
                    if post_data["post_type"] == "TIKTOK_VIDEO"
                    else None
                ),
                "photo_cover_index": None,
                "photo_images": (
                    [media_item["url"] for media_item in post_data["media"]]
                    if post_data["post_type"] == "TIKTOK_IMAGE"
                    else None
                ),
            },
        }

        # Determine media_type and add to payload
        media_type = (
            "PHOTO"
            if post_data["media"][0]["media_type"] == "IMAGE"
            else post_data["media"][0]["media_type"]
        )
        payload["media_type"] = media_type

        # Construct the PostModel with the validated payload
        result = PostModel(**payload)
        return result
