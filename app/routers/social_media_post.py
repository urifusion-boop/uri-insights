from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency
from app.repository.SocialMediaPostRepository import SocialMediaPostRepository
from app.domain.schemas.socialmediapost_schema import (
    SocialMediaPostCreate,
    SocialMediaPostUpdate,
)
from app.domain.responses.uri_response import UriResponse
from typing import Optional, List
from fastapi.encoders import jsonable_encoder

router = APIRouter()


# Create a new social media post
@router.post("/create")
async def create_post(
    post: SocialMediaPostCreate, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await SocialMediaPostRepository.create_post(db, post)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Create multiple social media posts
@router.post("/multipleCreate")
async def create_posts(
    posts: List[SocialMediaPostCreate],
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await SocialMediaPostRepository.multiple_create_posts(db, posts)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Get a social media post by ID
@router.get("/getById")
async def get_post(post_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)):
    data = await SocialMediaPostRepository.get_post_by_id(db, post_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Filter posts by user, platform, status, post type, with pagination
@router.get("/getByFilters")
async def filter_posts(
    user_id: str,
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    post_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    if platform:
        platform = str.upper(platform or "")
    data = await SocialMediaPostRepository.get_posts_by_filters(
        db=db,
        user_id=user_id,
        platform=platform,
        status=status,
        post_type=post_type,
        skip=skip,
        limit=limit,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update a social media post
@router.post("/update")
async def update_post(
    request: SocialMediaPostUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await SocialMediaPostRepository.update_post(db, request)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update post status
@router.post("/updateStatus")
async def update_post_status(
    post_id: str, status: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await SocialMediaPostRepository.update_post_status(db, post_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Delete a social media post
@router.delete("/delete")
async def delete_post(
    post_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await SocialMediaPostRepository.delete_post(db, post_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Search posts by text query
@router.get("/search")
async def search_posts(
    query: str,
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await SocialMediaPostRepository.search_posts(db, query, skip, limit)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
