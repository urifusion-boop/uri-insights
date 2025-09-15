from fastapi import APIRouter, Depends, Query
from app.dependencies import (
    enforce_feature_limit,
    get_db_dependency,
)
from app import schemas
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.TrackerRepository import TrackerRepository
from typing import Optional
from app.domain.responses.uri_response import UriResponse
from typing import Optional, List, Any
from fastapi.encoders import jsonable_encoder

from app.services.TrackerService import TrackerService

router = APIRouter()


@router.post("/create")
async def create_tracker(
    tracker: schemas.TrackerCreate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    _=Depends(enforce_feature_limit),
):
    data = await TrackerService.create_tracker(db=db, tracker=tracker)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/getById")
async def query_tracker(
    tracker_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await TrackerRepository.get_tracker_by_id(db=db, tracker_id=tracker_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/getByFilters")
async def filter_trackers(
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[str] = Query(None),
    keywords: Optional[List[str]] = Query(None),
    tracker_type: Optional[str] = Query(None),
    platforms: Optional[List[str]] = Query(None),
    locations: Optional[List[str]] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
) -> Any:
    data = await TrackerRepository.get_trackers_by_filter(
        db=db,
        user_id=user_id,
        keywords=keywords,
        tracker_type=tracker_type,
        platforms=platforms,
        locations=locations,
        skip=skip,
        limit=limit,
    )

    response = jsonable_encoder(data)

    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/update")
async def update_tracker(
    tracker: schemas.TrackerUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await TrackerRepository.update_tracker(db=db, tracker=tracker)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.delete("/delete")
async def delete_tracker(
    tracker_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await TrackerService.delete_tracker(db=db, tracker_id=tracker_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/getAlertSubscribedTrackers")
async def get_alert_subscribed_trackers(
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    API to get trackers where is_alert_subscribed is True.
    """
    data = await TrackerRepository.get_alert_subscribed_trackers(
        db=db, skip=skip, limit=limit
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
