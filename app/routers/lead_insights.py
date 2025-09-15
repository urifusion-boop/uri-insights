from fastapi import APIRouter, BackgroundTasks, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import enforce_feature_limit, get_db_dependency
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.filetype_enum import FileTypeEnum
from app.domain.enums.lead_enum import (
    LeadIndustryTypeEnum,
    LeadStatusEnum,
    LeadInterestLevelEnum,
    LeadSourceEnum,
)
from app.domain.schemas.leadbusinessinfo_schema import (
    LeadBusinessInfoCreate,
    LeadBusinessInfoUpdate,
)
from app.repository.LeadBusinessInfoRepository import LeadBusinessInfoRepository
from app.repository.LeadRepository import LeadRepository
from app.domain.schemas.lead_schema import (
    LeadCreate,
    LeadUpdate,
)
from app.domain.responses.uri_response import UriResponse
from typing import Optional, List, Union
from fastapi.encoders import jsonable_encoder
from app.services.ApolloService import ApolloService
from app.services.LeadBusinessInfoService import LeadBusinessInfoService
from app.services.LeadService import LeadService
from app.domain.requests.lead_requests import (
    GetLeadsByFiltersRequest,
    LeadAnalyticsRequest,
    LeadEnrichmentRequest,
)
from app.domain.enums.leadform_enum import LeadFormTypeEnum


router = APIRouter()


# Create a new lead
@router.post("/create")
async def create_lead(
    lead: LeadCreate, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = LeadRepository.create_lead(db, lead)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Create multiple leads
@router.post("/multipleCreate")
async def create_leads(
    leads: List[LeadCreate], db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.multiple_create_leads(db, leads)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Get a lead by ID
@router.get("/getById")
async def get_lead(lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)):
    data = await LeadRepository.get_lead_by_id(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Filter leads by assigned_to, status, interest level, source with pagination
@router.get("/getByFilters")
async def filter_leads(
    date_filter: Optional[DateFilterEnum] = None,
    filters: GetLeadsByFiltersRequest = Depends(),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.get_leads_by_filters(
        db=db,
        filters=filters,
        date_filter=date_filter,
        skip=skip,
        limit=limit,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update a lead
@router.post("/update")
async def update_lead(
    lead_id: str,
    updates: LeadUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.update_lead(db, lead_id, updates)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/updateMany")
async def update_many_leads(
    lead_ids: List[str],
    updates: LeadUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.update_many_leads(db, lead_ids, updates)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update lead status
@router.post("/updateStatus")
async def update_lead_status(
    lead_id: str, status: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.update_lead_status(db, lead_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Star a lead
@router.post("/star")
async def star_lead(
    lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.star_lead(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Unstar a lead
@router.post("/unstar")
async def unstar_lead(
    lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.unstar_lead(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.put("/emailed/update")
async def update_lead_emailed_status(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    status: bool = True,
):
    data = await LeadRepository.update_emailed(db, lead_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.put("/called/update")
async def update_lead_called_status(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    status: bool = True,
):
    data = await LeadRepository.update_called(db, lead_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Delete a lead
@router.delete("/delete")
async def delete_lead(
    lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadService.delete_lead(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.delete("/delete-many")
async def delete_many_leads(
    lead_ids: List[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.delete_many_leads(db, lead_ids)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Search leads by text query
@router.get("/search")
async def search_leads(
    query: str,
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.search_leads(db, query, skip, limit)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/analytics", response_model=dict)
async def get_lead_analytics(
    request: LeadAnalyticsRequest = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get analytics data for leads based on filtering options.
    """
    data = await LeadRepository.fetch_lead_analytics(db, request)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/business-info/create")
async def create_lead_business_info(
    lead_business_info: LeadBusinessInfoCreate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadBusinessInfoService.create_lead_business_info(
        db=db, background_tasks=background_tasks, lead_business_info=lead_business_info
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/business-info/getById")
async def get_lead_business_info_by_id(
    lead_business_info_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadBusinessInfoRepository.get_lead_business_info_by_id(
        db, lead_business_info_id
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/business-info/getByFilters")
async def get_lead_business_info_by_filter(
    user_id: str,
    business_name: Optional[str] = Query(None),
    business_website: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadBusinessInfoRepository.get_lead_business_info_by_filters(
        db, user_id, business_name, business_website, skip, limit
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/business-info/update")
async def update_lead_business_info(
    lead_business_info_id: str,
    updates: LeadBusinessInfoUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadBusinessInfoService.update_leads_business_info(
        db=db,
        lead_business_info_id=lead_business_info_id,
        updates=updates,
        background_tasks=background_tasks,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.delete("/business-info/delete")
async def delete_lead_business_info(
    lead_business_info_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadBusinessInfoRepository.delete_leads_business_info(
        db, lead_business_info_id
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/enrich")
async def enrich_lead(
    request: LeadEnrichmentRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    _=Depends(enforce_feature_limit),
):
    result = await ApolloService.handle_enrichment_request(
        lead_ids=request.lead_ids,
        db=db,
        reveal_email=request.reveal_email,
        reveal_phone=request.reveal_phone,
        webhook_url=request.webhook_url,
    )
    return UriResponse.get_status_response(response=jsonable_encoder(result))


@router.post("/regenerate-lead-follow-up-message")
async def regenerate_lead_follow_up_message(
    lead_id: str,
    user_prompt: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadService.regenerate_lead_follow_up_message(lead_id, user_prompt, db)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/export-lead")
async def export_lead_report(
    file_type: FileTypeEnum,
    assigned_to: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    date_filter: Optional[DateFilterEnum] = None,
    filters: GetLeadsByFiltersRequest = Depends(),
    skip: int = 0,
    limit: int = 10,
):
    filters.assigned_to = assigned_to
    await LeadService.export_leads_data(
        file_type=file_type,
        db=db,
        filters=filters,
        date_filter=date_filter,
        skip=skip,
        limit=limit,
    )
    return UriResponse.get_single_data_response(
        "Lead report", {"text": "File is being generated"}
    )


@router.delete("/delete-my-leads")
async def delete_my_leads(
    user_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.delete_all_leads_for_user(db, user_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/trigger-leads-gen")
async def trigger_conversational_leads_gen(
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    background_tasks.add_task(
        LeadService.generate_conversational_leads_background_job, db
    )

    return UriResponse.custom_response("Leads gen triggered successfully.", 202, True)
