from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency
from app.domain.requests.leadformsnapshot_requests import LeadFormSnapshotFilterQuery
from app.repository.LeadFormSnapshotRepository import LeadFormSnapshotRepository
from app.domain.responses.uri_response import UriResponse
from app.services.LeadFormSnapshotService import LeadFormSnapshotService

router = APIRouter()


@router.get("/getById")
async def get_snapshot_by_id(
    lead_form_snapshot_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormSnapshotRepository.get_by_id(db, lead_form_snapshot_id)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result["responseCode"],
    )


@router.get("/getByLeadFormId")
async def get_snapshots_by_lead_form_id(
    lead_form_id: str,
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormSnapshotRepository.get_all_by_lead_form_id(
        db, lead_form_id, skip, limit
    )
    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result["responseCode"],
    )


@router.get("/getByUserId")
async def get_snapshots_by_user_id(
    user_id: str,
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    filters = {"user_id": user_id}
    result = await LeadFormSnapshotService.get_by_filters(db, filters, skip, limit)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result["responseCode"],
    )


@router.get("/getByFilters")
async def get_snapshots_by_filters(
    filters: LeadFormSnapshotFilterQuery = Depends(),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    query = filters.model_dump(exclude_none=True)

    result = await LeadFormSnapshotService.get_by_filters(db, query, skip, limit)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result["responseCode"],
    )


@router.get("/getLatestSnapshot")
async def get_latest_snapshot(
    filters: LeadFormSnapshotFilterQuery = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    query = filters.model_dump(exclude_none=True)
    result = await LeadFormSnapshotRepository.get_latest_snapshot(db, query)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result["responseCode"],
    )


@router.delete("/delete")
async def delete_snapshot(
    lead_form_snapshot_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormSnapshotRepository.delete(db, lead_form_snapshot_id)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result["responseCode"],
    )
