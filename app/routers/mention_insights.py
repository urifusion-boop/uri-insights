from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency
from app.domain.requests.mention_requests import AlertAnalyticsRequest
from app.repository.MentionRepository import MentionRepository
from app.domain.schemas.mention_schema import MentionCreate, MentionUpdate
from app.domain.responses.uri_response import UriResponse
from typing import Optional, List
from fastapi.encoders import jsonable_encoder

from app.services.MentionService import MentionService

router = APIRouter()


# Create a new mention
@router.post("/create")
async def create_mention(
    mention: MentionCreate, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await MentionRepository.create_mention(db, mention)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Create multiple mentions
@router.post("/multipleCreate")
async def create_mentions(
    mentions: List[MentionCreate], db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await MentionRepository.multiple_create_mentions(db, mentions)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Get a mention by ID
@router.get("/getById")
async def get_mention(
    mention_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await MentionRepository.get_mention_by_id(db, mention_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Filter mentions by user_id, deleted, unread, read, starred with pagination
@router.get("/getByFilters")
async def filter_mentions(
    user_id: Optional[str] = Query(None),
    deleted: Optional[bool] = Query(None),
    unread: Optional[bool] = Query(None),
    read: Optional[bool] = Query(None),
    starred: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await MentionRepository.get_mentions_by_filters(
        db=db,
        user_id=user_id,
        deleted=deleted,
        unread=unread,
        read=read,
        starred=starred,
        skip=skip,
        limit=limit,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update a mention
@router.post("/update")
async def update_mention(
    mention_id: str,
    updates: MentionUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await MentionRepository.update_mention(db, mention_id, updates)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Mark a mention as read
@router.post("/markAsRead")
async def mark_as_read(
    mention_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await MentionRepository.mark_as_read(db, mention_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Mark a mention as starred
@router.post("/markAsStarred")
async def mark_as_starred(
    mention_id: str,
    starred: bool,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await MentionRepository.mark_as_starred(db, mention_id, starred)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Soft-delete a mention
@router.delete("/delete")
async def delete_mention(
    mention_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await MentionRepository.delete_mention(db, mention_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# @router.get("/track/set_mentions")
# async def track_and_set_mention(db: AsyncIOMotorDatabase = Depends(get_db_dependency)):
#     data = MentionRepository.track_keywords_and_set_mentions(db)
#     response = jsonable_encoder(data)
#     return UriResponse.get_status_response(
#         response=response, status_code=response["responseCode"]
#     )


@router.get("/analytics")
async def get_alerts_analytics(
    request: AlertAnalyticsRequest = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await MentionService.generate_alert_analytics(db, request)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
