from datetime import datetime
from pydantic import BaseModel
from typing import Any, List, Optional, Dict

from app.domain.enums.facebook_enum import FacebookFileTypeEnum


class FacebookPostPayload(BaseModel):
    """
    Represents the payload for creating a Facebook post.
    """

    message: Optional[str] = None  # The text content of the post.
    link: Optional[str] = None  # A URL to include in the post.
    published: Optional[bool] = True  # Whether to publish immediately (default: True).
    scheduled_publish_time: Optional[int] = (
        None  # UNIX timestamp for scheduling the post.
    )
    attached_media: Optional[List[Dict[str, str]]] = []


class FacebookPhotoPayload(BaseModel):
    """
    Represents the payload for uploading a photo to a Facebook Page.
    """

    url: str  # URL of the photo to upload.
    caption: Optional[str] = None  # Caption for the photo.
    published: Optional[bool] = True
    media_type: str
    alt_text: str | None


class FacebookUpdatePostPayload(BaseModel):
    """
    Represents the payload for updating an existing Facebook post.
    """

    message: str  # Updated text content of the post.


class FacebookUploadFile(BaseModel):
    """
    Represents the data required to start a file upload session
    """

    file_name: str
    file_length: int
    file_type: FacebookFileTypeEnum

    class Config:
        use_enum_values = True


class FacebookVideoPayload(BaseModel):
    """
    Represents the payload for initializing a video/document upload to a Facebook Page.
    """

    title: str  # Title of the video.
    description: Optional[str] = None  # Description of the video.
    video_url: str  # Path to video file received after uploading the video.
    # published: Optional[bool] = True
    file_data: FacebookUploadFile  # Data for the file to be uploaded.
    media_type: str


class FacebookSocialMediaPostSettings(BaseModel):
    targeting: str
    page_id: str
    title: str
    description: str
    file_data: Optional[FacebookUploadFile]


class FacebookMultipleMediaPayload(FacebookPostPayload):
    """
    Represents the payload for uploading multiple media items to Facebook.
    """

    attached_media: Optional[List[Dict[str, Any]]] = []
    # media_ids: Optional[List[str]] = []


class FacebookReelVideoPayload(BaseModel):
    video_url: str
    description: str


class FacebookInsightsParameters(BaseModel):
    entity_id: str
    metrics: str
    metric_type: Optional[str] = None
    period: Optional[str] = "day"
    access_token: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    previous: Optional[str] = None
    next: Optional[str] = None
