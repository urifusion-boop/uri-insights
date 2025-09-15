from pydantic import BaseModel
from typing import List, Optional
from app.domain.enums.tiktok_enum import PrivacyLevelEnum, SourceTypeEnum, TiktokMediaTypeEnum


# Pydantic Models
class PostInfo(BaseModel):
    title: str
    privacy_level: PrivacyLevelEnum
    disable_duet: Optional[bool] = False
    disable_comment: Optional[bool] = False
    disable_stitch: Optional[bool] = False
    video_cover_timestamp_ms: Optional[int] = None
    description: Optional[str] = None
    auto_add_music: Optional[bool] = False


class SourceInfo(BaseModel):
    source: SourceTypeEnum
    video_size: Optional[int] = None  # Required for FILE_UPLOAD
    chunk_size: Optional[int] = None  # Required for FILE_UPLOAD
    total_chunk_count: Optional[int] = None  # Required for FILE_UPLOAD
    video_url: Optional[str] = None  # Required for PULL_FROM_URL
    photo_cover_index: Optional[int] = None  # Optional for PHOTO uploads
    photo_images: Optional[List[str]] = None  # Required for PHOTO uploads


class PostModel(BaseModel):
    post_info: PostInfo
    source_info: SourceInfo
    media_type: TiktokMediaTypeEnum

class TiktokSocialMediaPostSettings(BaseModel):
    privacy_level: PrivacyLevelEnum
    disable_duet: bool
    disable_comment: bool
    disable_stitch: bool
    video_cover_timestamp_ms: int
    description: str
    auto_add_music: bool
