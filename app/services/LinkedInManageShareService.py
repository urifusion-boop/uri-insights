from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from http import HTTPStatus
import requests

from app.core.helpers.file_helper import FileHelper
from app.domain.enums.linkedin_enum import LinkedInMediaShareTypeEnum
from app.domain.requests.linkedin_requests import (
    ComLinkedinUgcShareMediaContent,
    MediaItem,
    RegisterUploadRequest,
    ServiceRelationship,
    ShareCommentary,
    ShareMediaContentPayload,
    ShareTextContentPayload,
    ShareArticleContentPayload,
    GetUploadUrlPayload,
    SpecificMediaContent,
)
from app.domain.responses.uri_response import UriResponse
from app.core.config import settings


class LinkedInManageShareService:
    BASE_URL = "https://api.linkedin.com/v2"
    BASE_HEADERS = {
        "LinkedIn-Version": settings.LINKEDIN_VERSION or "202401",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    @staticmethod
    async def create_share_text_content(
        payload: ShareTextContentPayload, access_token: Optional[str]
    ) -> Dict[str, Any]:

        headers = {
            **LinkedInManageShareService.BASE_HEADERS,
            "Authorization": f"Bearer {access_token}",
        }
        url = f"{LinkedInManageShareService.BASE_URL}/ugcPosts"
        response = requests.post(url, json=payload.dict(by_alias=True), headers=headers)
        if response.status_code != HTTPStatus.CREATED:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("message", "Failed to create text share."),
            )
        return UriResponse.create_response(
            "Share", response.json(), "Text Share successfully created."
        )

    @staticmethod
    async def create_share_article_content(
        payload: ShareArticleContentPayload, access_token: Optional[str]
    ) -> Dict[str, Any]:
        headers = {
            **LinkedInManageShareService.BASE_HEADERS,
            "Authorization": f"Bearer {access_token}",
        }
        url = f"{LinkedInManageShareService.BASE_URL}/ugcPosts"
        response = requests.post(url, json=payload.dict(by_alias=True), headers=headers)
        if response.status_code != HTTPStatus.CREATED:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to create article share."
                ),
            )

        return UriResponse.create_response(
            "Share", response.json(), "Article Share successfully created."
        )

    @staticmethod
    def __construct_get_upload_url_payload(
        author: str,
        file_type: str,
    ) -> GetUploadUrlPayload:
        owner_urn = author
        register_upload_request = RegisterUploadRequest(
            recipes=[f"urn:li:digitalmediaRecipe:feedshare-{file_type}"],
            owner=owner_urn,
            service_relationships=[
                ServiceRelationship(
                    relationship_type="OWNER", identifier="urn:li:userGeneratedContent"
                )
            ],
        )
        payload = GetUploadUrlPayload(register_upload_request=register_upload_request)
        return payload

    @staticmethod
    async def __get_upload_url(
        payload: GetUploadUrlPayload, access_token: str
    ) -> Dict[str, Any]:
        headers = {
            **LinkedInManageShareService.BASE_HEADERS,
            "Authorization": f"Bearer {access_token}",
        }
        url = f"{LinkedInManageShareService.BASE_URL}/assets?action=registerUpload"
        response = requests.post(url, json=payload.dict(by_alias=True), headers=headers)
        return response.json()

    @staticmethod
    async def __upload_image_or_video(
        url: str,
        file_path: str,
        access_token: str,
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        try:
            with open(file_path, "rb") as file:
                response = requests.put(url, headers=headers, data=file)
        except FileNotFoundError:
            data = await FileHelper.download_file_as_binary(file_path)
            response = requests.put(url, headers=headers, data=data)
        except Exception as e:
            print("Error uploading linkedin image or video: ", e)
            return UriResponse.create_response("File", None, "Failed to upload file.")
        response.raise_for_status()
        return UriResponse.create_response(
            "File", response, "File uploaded successfully."
        )

    @staticmethod
    def __construct_share_media_content_payload(
        author: str,
        commentary_text: str,
        media_items: List[MediaItem],
        file_type: LinkedInMediaShareTypeEnum,
    ) -> ShareMediaContentPayload:
        # Construct the nested fields
        share_commentary = ShareCommentary(text=commentary_text)
        specific_content = SpecificMediaContent(
            com_linkedin_ugc_ShareContent=ComLinkedinUgcShareMediaContent(
                shareCommentary=share_commentary,
                shareMediaCategory=file_type,
                media=media_items,
            )
        )

        # Construct the top-level payload
        payload = ShareMediaContentPayload(
            author=author,
            lifecycleState="PUBLISHED",
            specificContent=specific_content,
            visibility={"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        )

        return payload

    @staticmethod
    async def create_media_share_content(
        payload: ShareMediaContentPayload, access_token: str
    ) -> Dict[str, Any]:
        headers = {
            **LinkedInManageShareService.BASE_HEADERS,
            "Authorization": f"Bearer {access_token}",
        }
        author = payload.author
        commentary_text = (
            payload.specificContent.com_linkedin_ugc_ShareContent.shareCommentary.text
        )
        media_items = payload.specificContent.com_linkedin_ugc_ShareContent.media

        if not media_items:
            raise ValueError("No media items provided in the payload.")

        for media_item in media_items:
            file_path = media_item.media
            file_type: Any = (
                payload.specificContent.com_linkedin_ugc_ShareContent.shareMediaCategory
            )
            upload_url_payload = (
                LinkedInManageShareService.__construct_get_upload_url_payload(
                    author, str(file_type).lower()
                )
            )
            upload_url_response = await LinkedInManageShareService.__get_upload_url(
                upload_url_payload,
                access_token,
            )
            upload_url = upload_url_response["value"]["uploadMechanism"][
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
            ]["uploadUrl"]
            media_url = upload_url_response["value"]["asset"]

            await LinkedInManageShareService.__upload_image_or_video(
                url=upload_url, file_path=file_path, access_token=access_token
            )
            media_item.media = media_url
        create_media_share_payload = (
            LinkedInManageShareService.__construct_share_media_content_payload(
                author=author,
                commentary_text=commentary_text,
                media_items=media_items,
                file_type=file_type,
            )
        )
        url = f"{LinkedInManageShareService.BASE_URL}/ugcPosts"
        response = requests.post(
            url, json=create_media_share_payload.dict(by_alias=True), headers=headers
        )
        if response.status_code != HTTPStatus.CREATED:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("message", "Failed to create media share."),
            )

        return UriResponse.create_response(
            "Share", response.json(), "Media Share successfully created."
        )

    @staticmethod
    async def get_share_by_id(
        share_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        headers = {
            **LinkedInManageShareService.BASE_HEADERS,
            "Authoization": f"Bearer {access_token}",
        }
        url = f"{LinkedInManageShareService.BASE_HEADERS}/shares/{share_id}"
        response = requests.get(url, headers=headers)
        return UriResponse.get_single_data_response(
            "Share", response.json(), "Share successfully retrieved."
        )
