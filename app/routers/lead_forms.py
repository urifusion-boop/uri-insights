from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.domain.schemas.leadform_schema import (
    BusinessLeadFormUpdate,
    ConversationalLeadFormUpdate,
    LeadFormCreate,
    OrganizationLeadFormUpdate,
    PersonLeadFormUpdate,
)
from app.repository.LeadFormRepository import LeadFormRepository
from app.domain.responses.uri_response import UriResponse
from app.domain.requests.leadform_requests import (
    AutoPopulationQuery,
    BusinessSearchFormInput,
    ConversationalSearchFormInput,
    LeadFormFilterQuery,
    PersonSearchFormInput,
    OrganizationSearchFormInput,
)
from app.services.LeadFormService import LeadFormService
from app.services.ConversationalLeadJobService import ConversationalLeadJobService

router = APIRouter()


@router.post("/person-search/create")
async def create_person_search_lead_form(
    data: PersonSearchFormInput,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    payload = LeadFormCreate(**data.dict())
    result = await LeadFormService.create(db, payload, background_tasks)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.post("/organization-search/create")
async def create_organization_lead_form(
    data: OrganizationSearchFormInput,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    payload = LeadFormCreate(**data.dict())
    result = await LeadFormService.create(db, payload, background_tasks)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.post("/business-search/create")
async def create_business_lead_form(
    data: BusinessSearchFormInput,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    payload = LeadFormCreate(**data.model_dump())
    result = await LeadFormService.create(db, background_tasks, payload)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.post("/conversation-search/create")
async def create_conversational_lead_form(
    data: ConversationalSearchFormInput,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    payload = LeadFormCreate(**data.model_dump())
    result = await LeadFormService.create(db, payload, background_tasks)

    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.post("/conversation-search/fetch-leads")
async def fetch_conversational_leads(
    lead_form_id: str,
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Fetch and analyze leads from social platforms for a conversational lead form.
    This endpoint triggers the ConversationalLeadJobService which includes intent analysis.
    """
    # Get the lead form
    lead_form_result = await LeadFormRepository.get_by_id(db, lead_form_id)

    if lead_form_result["responseCode"] != 200:
        return UriResponse.get_status_response(
            response={"message": "Lead form not found"},
            status_code=404
        )

    lead_form = lead_form_result.get("responseData")

    if not lead_form:
        return UriResponse.get_status_response(
            response={"message": "Lead form data not found"},
            status_code=404
        )

    # Trigger the background job to fetch and analyze leads
    try:
        await ConversationalLeadJobService.fetch_leads_from_platforms(
            db=db,
            lead_form=lead_form,
            user_id=user_id
        )

        return UriResponse.get_status_response(
            response={
                "status": True,
                "responseCode": 200,
                "responseMessage": "Lead fetching and intent analysis completed successfully",
                "responseData": {"lead_form_id": lead_form_id}
            },
            status_code=200
        )
    except Exception as e:
        print(f"Error in fetch_conversational_leads endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.get_status_response(
            response={"message": f"Error fetching leads: {str(e)}", "lead_form_id": lead_form_id},
            status_code=500
        )


@router.post("/auto-populate")
async def auto_populate_lead_form(
    request: AutoPopulationQuery,
):
    result = await LeadFormService.auto_populate_lead_form(**request.dict())
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.get("/getById")
async def get_by_id(
    lead_form_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormRepository.get_by_id(db, lead_form_id)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.put("/person-search/update")
async def update_person_lead_form(
    lead_form_id: str,
    data: PersonLeadFormUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormService.update_apollo_lead_forms(
        db, data, lead_form_id, background_tasks
    )
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.put("/organization-search/update")
async def update_organization_lead_form(
    lead_form_id: str,
    data: OrganizationLeadFormUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormService.update_apollo_lead_forms(
        db, data, lead_form_id, background_tasks
    )
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.put("/conversation-search/update")
async def update_conversational_lead_form(
    lead_form_id: str,
    data: ConversationalLeadFormUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormService.update_conversational_lead_form(
        db, updates=data, lead_form_id=lead_form_id
    )
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.put("/business-search/update")
async def update_business_lead_form(
    lead_form_id: str,
    data: BusinessLeadFormUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormService.update_business_lead_form(
        db, lead_form_id, data, background_tasks
    )
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.get("/getByUserId")
async def get_by_user_id(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    filters = {"user_id": user_id}

    results = await LeadFormService.get_by_filters(db=db, filters=filters)

    return UriResponse.get_status_response(
        response=jsonable_encoder(results), status_code=results["responseCode"]
    )


@router.get("/getByFilters")
async def get_by_filters(
    data: LeadFormFilterQuery = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    filters = data.dict(exclude_none=True, exclude_unset=True)

    results = await LeadFormService.get_by_filters(db=db, filters=filters)

    return UriResponse.get_status_response(
        response=jsonable_encoder(results), status_code=results["responseCode"]
    )


# @router.post("/ai-leads/generate")
# async def generate_ai_leads(
#     lead_form_id: str,
#     background_tasks: BackgroundTasks,
#     db: AsyncIOMotorDatabase = Depends(get_db_dependency),
# ):
#     result = await LeadFormService.trigger_ai_leads_gen(
#         lead_form_id, db, background_tasks
#     )

#     return UriResponse.get_status_response(
#         response=jsonable_encoder(result), status_code=result["responseCode"]
#     )


@router.delete("/delete")
async def delete(
    lead_form_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormRepository.delete(db, lead_form_id)

    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )
