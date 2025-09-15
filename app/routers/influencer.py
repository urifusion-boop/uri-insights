from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import (
    enforce_feature_limit,
    get_db_dependency,
)
from app.domain.enums.account_enum import AccountTypeEnum
from app.repository.InfluencerRepository import InfluencerRepository
from app.domain.responses.uri_response import UriResponse
from typing import Optional
from fastapi.encoders import jsonable_encoder
from app.domain.schemas import influencer_schema
from app.services.InfluencerService import InfluencerService

router = APIRouter()


# Create a new influencer
@router.post("/create")
async def create_influencer(
    influencer: influencer_schema.InfluencerCreate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    _=Depends(enforce_feature_limit),
):
    data = await InfluencerService.create_influencer(db=db, influencer=influencer)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Get an influencer by ID
@router.get("/getById")
async def get_influencer(
    influencer_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await InfluencerRepository.get_influencer_by_id(db, influencer_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Filter influencers by name, email, platform, or location with pagination
@router.get("/getByFilters")
async def filter_influencers(
    user_id: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    platforms: Optional[str] = Query(
        None, description="Comma separated list of platforms"
    ),
    location: Optional[str] = Query(None),
    connected: Optional[bool] = Query(None),
    account_type: Optional[AccountTypeEnum] = Query(None),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await InfluencerRepository.get_influencers_by_filter(
        db=db,
        user_id=user_id,
        name=name,
        email=email,
        platforms=platforms.split(",") if platforms else None,
        location=location,
        connected=connected,
        account_type=account_type,
        skip=skip,
        limit=limit,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update an influencer's information
@router.post("/update")
async def update_influencer(
    influencer: influencer_schema.InfluencerUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await InfluencerRepository.update_influencer(db, influencer)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Delete an influencer by ID
@router.delete("/delete")
async def delete_influencer(
    influencer_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await InfluencerService.delete_influencer(db, influencer_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.delete("/delete_influencer_facebook")
async def delete_influencer_facebook(
    facebook_page_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await InfluencerRepository.delete_influencer_facebook(db, facebook_page_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
