from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from http import HTTPStatus
import requests
from app.domain.requests.twitter_requests import (
    MediaInitPayload,
    MediaAppendPayload,
    MediaFinalizePayload,
    MediaStatusPayload,
    MediaMetadataPayload,
    MediaSubtitlesDeletePayload,
)
from app.domain.enums.twitter_enum import (
    MediaCategory,
)


class XMediaUploadService:
    BASE_URL = "https://upload.twitter.com/1.1/media/upload.json"
    BASE_URL_SIMPLE_UPLOAD = "https://upload.twitter.com/1.1/media/upload.json"

    @staticmethod
    def init_upload(access_token: str, payload: MediaInitPayload) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            XMediaUploadService.BASE_URL, headers=headers, data=payload.dict()
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to initialize media upload."
                ),
            )
        return response.json()

    @staticmethod
    def append_upload(access_token: str, payload: MediaAppendPayload) -> None:
        headers = {"Authorization": f"Bearer {access_token}"}
        files = {"media": payload.media} if payload.media else None
        data = payload.dict(exclude={"media"})
        response = requests.post(
            XMediaUploadService.BASE_URL, headers=headers, data=data, files=files
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to append media upload."),
            )

    @staticmethod
    def finalize_upload(
        access_token: str, payload: MediaFinalizePayload
    ) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            XMediaUploadService.BASE_URL, headers=headers, data=payload.dict()
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to finalize media upload."),
            )
        return response.json()

    @staticmethod
    def get_upload_status(
        access_token: str, payload: MediaStatusPayload
    ) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            XMediaUploadService.BASE_URL, headers=headers, params=payload.dict()
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to retrieve upload status."
                ),
            )
        return response.json()

    @staticmethod
    def attach_metadata(access_token: str, payload: MediaMetadataPayload) -> None:
        url = "https://upload.twitter.com/1.1/media/metadata/create.json"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=payload.dict())
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to attach media metadata."),
            )

    @staticmethod
    def delete_subtitles(
        access_token: str, payload: MediaSubtitlesDeletePayload
    ) -> None:
        url = "https://upload.twitter.com/1.1/media/subtitles/delete.json"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=payload.dict())
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to delete media subtitles."
                ),
            )

    @staticmethod
    def upload_media(
        access_token: str,
        media: bytes,
        media_category: Optional[MediaCategory] = None,
        additional_owners: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Upload an image or GIF using the simple upload endpoint.

        :param access_token: Bearer token for authentication.
        :param media: The raw binary content of the file being uploaded.
        :param media_category: (Optional) Media category for Ads API or specific use cases.
        :param additional_owners: (Optional) List of user IDs allowed to use the media.
        :return: JSON response containing the media_id and other metadata.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        files = {"media": media}
        data = {
            "media_category": media_category.value if media_category else None,
            "additional_owners": (
                ",".join(map(str, additional_owners)) if additional_owners else None
            ),
        }
        response = requests.post(
            XMediaUploadService.BASE_URL_SIMPLE_UPLOAD,
            headers=headers,
            data=data,
            files=files,
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to upload media."),
            )
        return response.json()
