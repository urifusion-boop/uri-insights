from typing import Optional
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi.encoders import jsonable_encoder
from app.services.AiRunService import AiRunService
from app.domain.requests.airun_requests import AiRunCreateRequest, AiRunUpdateRequest
from app.domain.responses.uri_response import UriResponse
from app.dependencies import get_db_dependency

router = APIRouter()


@router.post("/create/{thread_id}", summary="Create a new AI Run")
async def create_run(
    thread_id: str,
    request_data: AiRunCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await AiRunService.create_run(db, thread_id, request_data)
    return UriResponse.get_status_response(response=response)


@router.get("/getById/{thread_id}/{run_id}", summary="Retrieve an AI Run by ID")
async def get_run(
    thread_id: str,
    run_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await AiRunService.get_run(db, thread_id, run_id)
    return UriResponse.get_status_response(response=response)


@router.get("/getByThread/{thread_id}", summary="List all AI Runs for a Thread")
async def get_all_runs(
    thread_id: str,
    limit: int = 20,
    order: str = "desc",
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await AiRunService.get_all_runs(db, thread_id, limit, order)
    return UriResponse.get_status_response(response=response)


@router.post("/update/{thread_id}/{run_id}", summary="Update metadata for an AI Run")
async def update_run(
    thread_id: str,
    run_id: str,
    request_data: AiRunUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await AiRunService.update_run(db, thread_id, run_id, request_data)
    return UriResponse.get_status_response(response=response)


@router.post("/cancel/{thread_id}/{run_id}", summary="Cancel an AI Run")
async def cancel_run(
    thread_id: str,
    run_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await AiRunService.cancel_run(db, thread_id, run_id)
    return UriResponse.get_status_response(response=response)
