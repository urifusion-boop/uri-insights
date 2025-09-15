from typing import Dict, List, Optional
from app.core.helpers.google_helper import GoogleHelper
from app.domain.enums.linkedin_enum import LinkedInTokenScopeEnum
from app.domain.requests.linkedin_requests import (
    ShareArticleContentPayload,
    ShareMediaContentPayload,
    ShareTextContentPayload,
)
from app.domain.schemas.influencer_schema import InfluencerCreate
from app.domain.enums.account_enum import AccountTypeEnum


class LinkedinHelper:
    @staticmethod
    def __construct_matching_dict_for_payload(payload: dict, account_type: str) -> dict:
        """
        Creates a dictionary with matching keys for the object BaseShareContentPayload
        :payload: Dictionary to transform
        :Returns: A dictionary
        """
        post_settings = payload.get("settings", None)
        if account_type == AccountTypeEnum.PROFESSIONAL:
            base_author_url = "urn:li:organization:"
        else:
            base_author_url = "urn:li:person:"
        result_dict = {
            "author": base_author_url + payload["social_user_id"],
            "lifecycleState": "PUBLISHED",
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": (
                    post_settings["visibility"] if post_settings else "PUBLIC"
                )
            },
        }
        return result_dict

    @staticmethod
    def create_linkedin_text_post_payload_from_dict(
        payload: dict, account_type: str
    ) -> ShareTextContentPayload:
        """
        Creates an instance of the linkedin text share from a dictionary
        :payload: Dictionary to transform
        :Returns: An instance of ShareTextContentPayload or None
        """
        result_dict = LinkedinHelper.__construct_matching_dict_for_payload(
            payload, account_type
        )
        specific_content = {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": payload.get("content", "")},
                "shareMediaCategory": "NONE",
            }
        }
        result_dict["specificContent"] = specific_content
        result_payload = ShareTextContentPayload(**result_dict)
        return result_payload

    @staticmethod
    def create_linkedin_article_post_payload_from_dict(
        payload: dict, account_type: str
    ) -> ShareArticleContentPayload:
        # LIMITATION: BECAUSE THE POST INSTANCE SAVED IN THE DB ONLY SAVES A SINGLE POST URL AND THERE IS NO
        # DESCRIPTION OR TITLE ATTACHED TO THE URL, THIS FUNCTION LIMITS THE ARTICLE SHARE TO SHARING JUST
        # A SINGLE LINK
        """
        Creates an instance of the linkedin article share from a dictionary
        :payload: Dictionary to transform
        :Returns: An instance of ShareArticleContentPayload or None
        """
        result_dict = LinkedinHelper.__construct_matching_dict_for_payload(
            payload, account_type
        )
        post_settings = payload.get("settings", None)
        specific_content = {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": payload.get("content", "")},
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": (
                                post_settings.get("description")
                                if post_settings
                                else ""
                            )
                        },
                        "originalUrl": payload.get("post_url"),
                        "title": {
                            "text": post_settings.get("title") if post_settings else ""
                        },
                    }
                ],
            }
        }
        result_dict["specificContent"] = specific_content
        result_payload = ShareArticleContentPayload(**result_dict)
        return result_payload

    @staticmethod
    def create_linkedin_media_post_payload_from_dict(
        payload: dict, account_type: str
    ) -> ShareArticleContentPayload:
        # LIMITATION: THE STRUCTURE OF THE POST SAVED IN THE DB SAVES A DIFFERENT MEDIA_TYPE
        # FOR EVERY MEDIA IN THE LIST. HOWEVER IN THE LINKEDIN API THOUGH WE CAN PASS MULTIPLE MEDIA
        # WE CAN ONLY PASS ONE MEDIA TYPE FOR ALL THOSE MEDIA WHICH MEANS THAT EVERY ITEM IN THE MEDIA
        # LIST SHOULD EITHER BE AN IMAGE OR A VIDEO
        """
        Creates an instance of the linkedin media share from a dictionary
        :payload: Dictionary to transform
        :Returns: An instance of ShareArticleContentPayload or None
        """
        result_dict = LinkedinHelper.__construct_matching_dict_for_payload(
            payload, account_type
        )
        post_settings = payload.get("settings", None)
        specific_content = {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": payload.get("content")},
                "shareMediaCategory": payload["media"][0]["media_type"],
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": (
                                post_settings.get("description")
                                if post_settings
                                else ""
                            )
                        },
                        "media": media_item.get("url"),
                        "title": {
                            "text": post_settings.get("title") if post_settings else ""
                        },
                    }
                    for media_item in payload["media"]
                ],
            }
        }
        result_dict["specificContent"] = specific_content
        result_payload = ShareMediaContentPayload(**result_dict)
        return result_payload

    @staticmethod
    def extract_relevant_page_data(page_data: dict) -> Dict:
        # Extract relevant fields with default values for missing keys
        vanity_name = page_data.get("vanityName", "")
        localized_name = page_data.get("localizedName", "")
        org_id = page_data.get("id", "")
        localized_description = page_data.get("localizedDescription", "")
        localized_website = page_data.get("localizedWebsite", "")
        logo_original = page_data.get("logoV2", {}).get("original")

        # Create a dictionary for the extracted data
        page_data = {
            "vanityName": vanity_name,
            "localizedName": localized_name,
            "id": org_id,
            "localizedDescription": localized_description,
            "localizedWebsite": localized_website,
            "logo": logo_original,
        }

        return page_data

    @staticmethod
    def construct_personal_influencer_creation_data(
        user_id: str,
        data: dict,
        access_token: str,
        token_scope: LinkedInTokenScopeEnum,
    ) -> InfluencerCreate:
        influencer_creation_data = InfluencerCreate(
            user_id=user_id,
            social_name=f"{data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}",
            profile_pic=data.get("profilePicture", {}).get("displayImage", ""),
            social_user_id=str(data.get("id", "")),
            social_username=data.get("vanityName", ""),
            social_platform="LINKEDIN",
            account_type=AccountTypeEnum.PERSONAL,
            connected=True,
            token={token_scope.value: access_token},
        )
        return influencer_creation_data

    @staticmethod
    def construct_organization_influencer_creation_data(
        user_id: str,
        data: dict,
        access_token: str,
        token_scope: LinkedInTokenScopeEnum,
    ) -> InfluencerCreate:
        influencer_creation_data = InfluencerCreate(
            user_id=user_id,
            social_name=data.get("localizedName", ""),
            profile_pic=data.get("logo", ""),
            social_user_id=str(data.get("id", "")),
            social_username=data.get("vanityName", ""),
            social_platform="LINKEDIN",
            account_type=AccountTypeEnum.PROFESSIONAL,
            connected=True,
            token={token_scope.value: access_token},
        )
        return influencer_creation_data

    @staticmethod
    def extract_data_for_ai_post_insights(linkedin_cached_data) -> List[dict]:
        posts = linkedin_cached_data.get("posts", [])
        tranformed_posts = []
        # Extract media information
        for post in posts:
            media_info = (
                post.get("specificContent", {})
                .get("com.linkedin.ugc.ShareContent", {})
                .get("media", [])
            )
            first_attachment = media_info[0] if media_info else {}

            transformed_data = {
                "media": {
                    "media_type": post.get("specificContent", {})
                    .get("com.linkedin.ugc.ShareContent", {})
                    .get("shareMediaCategory", "unknown"),
                    "caption": first_attachment.get("description", {}).get(
                        "text", "No caption"
                    ),
                },
                "timestamp": post.get("firstPublishedAt", None),
            }
            tranformed_posts.append(transformed_data)
        return tranformed_posts
