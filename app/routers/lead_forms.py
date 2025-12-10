from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import enforce_feature_limit, get_db_dependency
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
 
from app.repository.LeadRepository import LeadRepository

router = APIRouter()


@router.post("/person-search/create")
async def create_person_search_lead_form(
    data: PersonSearchFormInput,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    _: dict = Depends(enforce_feature_limit),
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
    _: dict = Depends(enforce_feature_limit),
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
    _: dict = Depends(enforce_feature_limit),
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
    Queue lead generation job for async processing by worker.
    Returns immediately with job_id for polling status.

    This endpoint is non-blocking - the job is sent to Azure Service Bus queue
    and processed by a separate worker process. Frontend should poll
    /conversation-search/job-status/{job_id} for progress.
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

    # Check feature limits before starting lead generation
    from app.middlewares.FeatureLimitMiddleware import FeatureLimitMiddleware, FeatureLimitExceeded
    from app.domain.enums.endpoints_enum import EndpointsEnum

    try:
        limit_check_result = await FeatureLimitMiddleware.verify_feature_limit(
            user_id=user_id,
            url_path=EndpointsEnum.LEAD_GEN.value
        )

        await FeatureLimitMiddleware.handle_feature_limit_result(
            db=db,
            result=limit_check_result,
            user_id=user_id,
            url_path=EndpointsEnum.LEAD_GEN.value
        )
    except FeatureLimitExceeded as e:
        return UriResponse.get_status_response(
            response={
                "message": str(e.message),
                "limit_exceeded": True
            },
            status_code=403
        )

    # Create job tracking document
    try:
        from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository
        from app.services.azure.producers.LeadGenerationProducer import LeadGenerationProducer
        from bson import json_util
        import json

        job_id = await LeadGenerationJobRepository.create_job(
            db=db,
            lead_form_id=lead_form_id,
            user_id=user_id,
            status="queued",
            progress=0,
            message="Job queued for processing..."
        )

        # Add job_id to lead_form for worker to track progress
        lead_form["job_id"] = job_id

        # Serialize lead_form to handle datetime objects - convert to ISO strings
        def serialize_datetime(obj):
            """Recursively convert datetime objects to ISO format strings"""
            if isinstance(obj, dict):
                return {k: serialize_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, '__dict__'):
                return serialize_datetime(obj.__dict__)
            return obj

        from datetime import datetime
        lead_form_serialized = serialize_datetime(lead_form)

        # Send to Azure Service Bus queue for async processing by worker
        # This is non-blocking and returns immediately
        await LeadGenerationProducer.send_lead_generation_job(
            lead_form_id=lead_form_id,
            user_id=user_id,
            lead_form=lead_form_serialized
        )

        print(f"✅ Lead generation job {job_id} queued successfully")

        # Return immediately with job_id
        return UriResponse.get_status_response(
            response={
                "status": True,
                "responseCode": 202,  # 202 Accepted
                "responseMessage": "Lead generation queued. Poll /conversation-search/job-status/{job_id} for progress.",
                "responseData": {
                    "lead_form_id": lead_form_id,
                    "job_id": job_id,
                    "status": "queued",
                    "poll_url": f"/conversation-search/job-status/{job_id}"
                }
            },
            status_code=202
        )
    except Exception as e:
        print(f"Error starting lead generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.get_status_response(
            response={"message": f"Error starting lead generation: {str(e)}", "lead_form_id": lead_form_id},
            status_code=500
        )


@router.get("/conversation-search/job-status/{job_id}")
async def get_job_status(
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Poll endpoint to check lead generation job status.
    Frontend should call this every 3-5 seconds until status is 'completed' or 'failed'.
    """
    print(f"[JOB_STATUS] Received request for job_id: {job_id}")
    try:
        from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository
        import asyncio

        print(f"[JOB_STATUS] Querying database for job_id: {job_id}")

        # Add timeout to prevent hanging (increased to 30s for slower database queries)
        job = await asyncio.wait_for(
            LeadGenerationJobRepository.get_job_status(db, job_id),
            timeout=30.0
        )

        print(f"[JOB_STATUS] Query result: {job is not None}")

        if not job:
            print(f"[JOB_STATUS] Job not found: {job_id}")
            return UriResponse.get_status_response(
                response={"message": "Job not found"},
                status_code=404
            )

        print(f"[JOB_STATUS] Returning job status: {job['status']}, progress: {job['progress']}")
        return UriResponse.get_status_response(
            response={
                "status": True,
                "responseCode": 200,
                "responseMessage": job["message"],
                "responseData": {
                    "job_id": job["job_id"],
                    "lead_form_id": job["lead_form_id"],
                    "status": job["status"],  # processing, completed, failed
                    "progress": job["progress"],  # 0-100
                    "message": job["message"],
                    "stats": job.get("stats"),  # Only available when completed
                    "error": job.get("error"),  # Only available when failed
                    "created_at": job["created_at"],
                    "updated_at": job["updated_at"]
                }
            },
            status_code=200
        )
    except asyncio.TimeoutError:
        print(f"[JOB_STATUS] Database query timed out for job_id: {job_id}")
        return UriResponse.get_status_response(
            response={"message": "Database query timed out"},
            status_code=500
        )
    except Exception as e:
        print(f"[JOB_STATUS] Error fetching job status: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.get_status_response(
            response={"message": f"Error fetching job status: {str(e)}"},
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
    _: dict = Depends(enforce_feature_limit),
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
    _: dict = Depends(enforce_feature_limit),
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
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormService.update_conversational_lead_form(
        db, lead_form_id=lead_form_id, updates=data, background_tasks=background_tasks
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
    _: dict = Depends(enforce_feature_limit),
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
