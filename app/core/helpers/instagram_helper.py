from typing import Optional
import requests

from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.instagram_enum import (
    InstagramMediaTypeEnum,
    InstagramTimeFrameEnum,
)
from app.domain.requests.instagram_requests import PostInstagramMediaRequest
from app.repository.InfluencerRepository import InfluencerRepository


class InstagramHelper:
    @staticmethod
    def construct_post_media_request(payload: dict) -> PostInstagramMediaRequest:
        media_type = (
            InstagramMediaTypeEnum.IMAGE
            if payload["media"][0]["media_type"] == "IMAGE"
            else InstagramMediaTypeEnum.REELS
        )
        post_media_request_dict = {
            "media_url": payload["media"][0]["url"],
            "media_type": media_type,
            "caption": payload["content"],
        }

        post_media_request = PostInstagramMediaRequest(**post_media_request_dict)

        return post_media_request

    @staticmethod
    async def extract_ids_from_webhook(webhook_data: dict) -> Optional[dict]:
        ids_dict = {}
        items = webhook_data.get("entry")
        if not items:
            print("No data returned in webhook")
            return None
        for item in items:
            ig_user_id = item.get("id")
            changes = item.get("changes", [])
            if len(changes) == 0:
                print("No changes found in webhook data")
                return None
            media_and_comment_ids = [change.get("value") for change in changes]

            ids_dict[ig_user_id] = media_and_comment_ids

        return ids_dict

    @staticmethod
    def map_datefilter_enum_to_timeframe_enum(
        date_info: DateFilterEnum,
    ) -> InstagramTimeFrameEnum:
        map = {
            DateFilterEnum.LAST_1_MONTH: InstagramTimeFrameEnum.LAST_30_DAYS,
            DateFilterEnum.LAST_1_WEEK: InstagramTimeFrameEnum.THIS_WEEK,
            DateFilterEnum.LAST_2_MONTHS: InstagramTimeFrameEnum.LAST_90_DAYS,
            DateFilterEnum.LAST_2_WEEKS: InstagramTimeFrameEnum.LAST_14_DAYS,
            DateFilterEnum.LAST_3_MONTHS: InstagramTimeFrameEnum.LAST_90_DAYS,
            DateFilterEnum.LAST_7_DAYS: InstagramTimeFrameEnum.THIS_WEEK,
        }

        return map.get(date_info, InstagramTimeFrameEnum.LAST_14_DAYS)
