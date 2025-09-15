from typing import Optional
from fastapi import APIRouter, Depends
from app.services.AiThreadService import AiThreadService
from app.domain.requests.aithread_requests import (
    AiThreadCreateRequest,
    AiThreadUpdateRequest,
)
from app.domain.responses.uri_response import UriResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import enforce_feature_limit, get_db_dependency
from fastapi.encoders import jsonable_encoder

router = APIRouter()


@router.post("/create", summary="Create a new AI Thread")
async def create_thread(
    user_id: str,
    thread_type: str,
    request_data: AiThreadCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    _: dict = Depends(enforce_feature_limit),
):
    response = await AiThreadService.create_thread(
        db, user_id, thread_type, request_data
    )
    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )


@router.get("/getById/{thread_id}", summary="Retrieve an AI Thread by ID")
async def get_thread(
    thread_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await AiThreadService.get_thread(db, thread_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )


@router.get("/getByFilters", summary="List AI Threads with Pagination")
async def list_threads(
    user_id: str,
    thread_type: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await AiThreadService.get_threads_by_filter(
        db, user_id, thread_type, limit, skip
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(response=response)


@router.post("/update", summary="Update an AI Thread")
async def update_thread(
    thread_id: str,
    request_data: AiThreadUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await AiThreadService.update_thread(db, thread_id, request_data)
    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )


@router.delete("/delete/{thread_id}", summary="Delete an AI Thread")
async def delete_thread(
    thread_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    response = await AiThreadService.delete_thread(db, thread_id)
    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )
