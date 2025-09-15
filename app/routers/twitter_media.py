from fastapi import APIRouter, Depends, UploadFile, Form, Query, File
from fastapi.responses import JSONResponse
from typing import List, Optional
from app.services.XMediaUploadService import XMediaUploadService
from app.domain.requests.twitter_requests import (
    MediaInitPayload,
    MediaAppendPayload,
    MediaFinalizePayload,
    MediaStatusPayload,
    MediaMetadataPayload,
    MediaSubtitlesDeletePayload,
)
from app.domain.enums.twitter_enum import MediaCategory
from app.core.auth_handler import get_x_access_token

router = APIRouter()


@router.post(
    "/init",
    response_model=dict,
    summary="Initialize Media Upload",
    description=(
        "**Purpose**: Start a media upload session and get a `media_id`.\n\n"
        "**Constraints**:\n"
        "- Maximum file size:\n"
        "  - **Images**: 5 MB\n"
        "  - **GIFs**: 15 MB\n"
        "  - **Videos**: 512 MB (with `media_category=tweet_video`)\n"
        "- Supported MIME types:\n"
        "  - Images: `image/jpeg`, `image/png`, `image/gif`, `image/webp`\n"
        "  - Videos: `video/mp4`\n"
        "- Advanced use cases require `media_category` (e.g., `tweet_image`, `tweet_video`)."
    ),
)
async def init_upload(
    total_bytes: int = Form(
        ..., description="The size of the media being uploaded in bytes."
    ),
    media_type: str = Form(
        ..., description="The MIME type of the media being uploaded."
    ),
    media_category: Optional[MediaCategory] = Form(
        None,
        description="The category of the media for specific constraints (e.g., `tweet_image`).",
    ),
    additional_owners: Optional[List[int]] = Form(
        None, description="List of user IDs allowed to use the `media_id`."
    ),
    access_token: str = Depends(get_x_access_token),
):
    """
    Start a new media upload session.

    - `total_bytes`: Size of the media in bytes.
    - `media_type`: MIME type of the media (e.g., `image/jpeg`).
    - `media_category`: Optional, advanced use case category (e.g., `tweet_video`).
    - `additional_owners`: Optional list of user IDs allowed to use the `media_id`.

    **Returns**:
    - `media_id`: A unique identifier for the upload session.
    """
    payload = MediaInitPayload(
        total_bytes=total_bytes,
        media_type=media_type,
        media_category=media_category,
        additional_owners=additional_owners,
    )
    result = XMediaUploadService.init_upload(access_token, payload)
    return JSONResponse(content=result)


@router.post(
    "/append",
    response_model=None,
    summary="Append Media Chunk",
    description=(
        "**Purpose**: Append a chunk of the media to the upload session.\n\n"
        "**Constraints**:\n"
        "- Chunks must be uploaded sequentially or in parallel.\n"
        "- Maximum chunk size: **5 MB**.\n"
        "- Segment indices start at `0` and increment for each chunk.\n"
        "- Maximum of **1,000 chunks** per upload session."
    ),
)
async def append_upload(
    media_id: str = Form(
        ..., description="The `media_id` returned from the INIT command."
    ),
    segment_index: int = Form(
        ..., description="Index of the file chunk being uploaded."
    ),
    file: UploadFile = File(None, description="The raw binary file content."),
    media_data: Optional[str] = Form(
        None,
        description="Base64-encoded chunk of the media (alternative to raw binary).",
    ),
    access_token: str = Depends(get_x_access_token),
):
    """
    Append a chunk of media to the upload session.

    - `media_id`: Media ID from the INIT command.
    - `segment_index`: Ordered index of the chunk.
    - `file`: Raw binary file content.
    - `media_data`: Base64-encoded chunk (alternative to `file`).

    **Returns**:
    - Success message indicating the chunk was appended.
    """
    file_bytes = await file.read() if file else None
    payload = MediaAppendPayload(
        media_id=media_id,
        segment_index=segment_index,
        media=file_bytes,
        media_data=media_data,
    )
    XMediaUploadService.append_upload(access_token, payload)
    return JSONResponse(content={"message": "Chunk uploaded successfully."})


@router.post(
    "/finalize",
    response_model=dict,
    summary="Finalize Media Upload",
    description=(
        "**Purpose**: Complete the media upload session.\n\n"
        "**Constraints**:\n"
        "- Call only after all chunks have been uploaded.\n"
        "- Large media files may require status polling if `processing_info` is returned."
    ),
)
async def finalize_upload(
    media_id: str = Form(
        ..., description="The `media_id` returned from the INIT command."
    ),
    access_token: str = Depends(get_x_access_token),
):
    """
    Finalize the media upload session.

    - `media_id`: Media ID from the INIT command.

    **Returns**:
    - Metadata for the uploaded media, including `media_id` and size.
    """
    payload = MediaFinalizePayload(media_id=media_id)
    result = XMediaUploadService.finalize_upload(access_token, payload)
    return JSONResponse(content=result)


@router.get(
    "/status",
    response_model=dict,
    summary="Check Media Upload Status",
    description=(
        "**Purpose**: Check the processing status of media files, especially large videos and GIFs.\n\n"
        "**Constraints**:\n"
        "- Use only if `processing_info` is returned by `/finalize`.\n"
        "- Polling intervals are indicated by `check_after_secs`."
    ),
)
async def check_upload_status(
    media_id: str, access_token: str = Depends(get_x_access_token)
):
    """
    Check the status of media processing.

    - `media_id`: Media ID from the INIT command.

    **Returns**:
    - Current processing state (`pending`, `in_progress`, `succeeded`, or `failed`).
    """
    payload = MediaStatusPayload(media_id=media_id)
    result = XMediaUploadService.get_upload_status(access_token, payload)
    return JSONResponse(content=result)


@router.post(
    "/metadata",
    response_model=None,
    summary="Attach Media Metadata",
    description=(
        "**Purpose**: Attach metadata (e.g., alt text) to uploaded media.\n\n"
        "**Constraints**:\n"
        "- Alt text must be ≤ 1,000 characters.\n"
        "- Metadata applies only to images and GIFs."
    ),
)
async def attach_metadata(
    media_id: str = Form(
        ..., description="The `media_id` returned from the INIT command."
    ),
    alt_text: Optional[str] = Form(
        None, description="Alt text for the media (e.g., image description)."
    ),
    access_token: str = Depends(get_x_access_token),
):
    """
    Attach metadata to media.

    - `media_id`: Media ID from the INIT command.
    - `alt_text`: Optional alt text for the media (up to 1,000 characters).

    **Returns**:
    - Success message after attaching metadata.
    """
    payload = MediaMetadataPayload(
        media_id=media_id, alt_text={"text": alt_text} if alt_text else None
    )
    XMediaUploadService.attach_metadata(access_token, payload)
    return JSONResponse(content={"message": "Metadata attached successfully."})


@router.post(
    "/subtitles/delete",
    response_model=None,
    summary="Delete Media Subtitles",
    description=(
        "**Purpose**: Delete subtitles from an uploaded video.\n\n"
        "**Constraints**:\n"
        "- Subtitle languages must use valid BCP-47 language codes (e.g., `en`, `es`).\n"
        "- Applies only to video media."
    ),
)
async def delete_subtitles(
    media_id: str = Form(..., description="The `media_id` of the associated video."),
    media_category: MediaCategory = Form(
        ...,
        description="The media category of the associated video (e.g., `tweet_video`).",
    ),
    subtitle_info: str = Form(
        ...,
        description="JSON string of subtitle details to delete (e.g., language codes).",
    ),
    access_token: str = Depends(get_x_access_token),
):
    """
    Delete subtitles from a video.

    - `media_id`: Media ID of the video.
    - `media_category`: Media category of the video.
    - `subtitle_info`: JSON string of subtitle details to delete.

    **Returns**:
    - Success message after deleting subtitles.
    """
    subtitle_info_dict = eval(subtitle_info)  # Convert JSON string to dictionary
    payload = MediaSubtitlesDeletePayload(
        media_id=media_id,
        media_category=media_category,
        subtitle_info=subtitle_info_dict,
    )
    XMediaUploadService.delete_subtitles(access_token, payload)
    return JSONResponse(content={"message": "Subtitles deleted successfully."})


@router.post(
    "/simple-upload",
    response_model=dict,
    summary="Simple Media Upload",
    description=(
        "**Purpose**: Upload smaller media files (e.g., images, GIFs) in a single request.\n\n"
        "**Constraints**:\n"
        "- Maximum file size:\n"
        "  - Images: 5 MB\n"
        "  - GIFs: 15 MB\n"
        "- Supported MIME types:\n"
        "  - Images: `image/jpeg`, `image/png`, `image/webp`, `image/gif`."
    ),
)
async def simple_upload(
    file: UploadFile = File(..., description="The raw binary file content."),
    media_category: Optional[MediaCategory] = Form(
        None,
        description="The category representing the media use case (e.g., `tweet_image`).",
    ),
    additional_owners: Optional[List[int]] = Form(
        None,
        description="Comma-separated list of user IDs allowed to use the media_id.",
    ),
    access_token: str = Depends(get_x_access_token),
):
    """
    Upload smaller media files (images, GIFs).

    - `file`: The raw binary file content.
    - `media_category`: Optional category (e.g., `tweet_image`).
    - `additional_owners`: Optional comma-separated list of user IDs.

    **Returns**:
    - Media metadata, including `media_id` and size.
    """
    file_bytes = await file.read()
    result = XMediaUploadService.upload_media(
        access_token=access_token,
        media=file_bytes,
        media_category=media_category,
        additional_owners=additional_owners,
    )
    return JSONResponse(content=result)
