from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import enforce_feature_limit, get_db_dependency
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.domain.schemas.leadform_schema import (
    BusinessLeadFormUpdate,
    ConversationalLeadFormUpdate,
    GoogleMapsLeadFormUpdate,
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
    GoogleMapsSearchFormInput,
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
    try:
        payload = LeadFormCreate(**data.dict())
        result = await LeadFormService.create(db, payload, background_tasks)
        return UriResponse.get_status_response(
            response=jsonable_encoder(result), status_code=result["responseCode"]
        )
    except Exception as e:
        print(f"\n❌ ERROR creating person search lead form:")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        print(f"   Received data: {data.dict() if hasattr(data, 'dict') else 'Unable to serialize'}")
        raise


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
    result = await LeadFormService.create(db, payload, background_tasks)
    return UriResponse.get_status_response(
        response=jsonable_encoder(result), status_code=result["responseCode"]
    )


@router.post("/google-maps-search/create")
async def create_google_maps_lead_form(
    data: GoogleMapsSearchFormInput,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Create a Google Maps lead form for local business discovery

    Supports both Text Search (natural language) and Nearby Search (precise location)
    """
    try:
        payload = LeadFormCreate(**data.model_dump())
        result = await LeadFormService.create(db, payload, background_tasks)
        return UriResponse.get_status_response(
            response=jsonable_encoder(result), status_code=result["responseCode"]
        )
    except Exception as e:
        print(f"\n❌ ERROR creating Google Maps lead form:")
        print(f"   Error: {str(e)}")
        return UriResponse.error_response(
            message=f"Failed to create Google Maps lead form: {str(e)}",
            error_code=500
        )


@router.post("/google-maps-search/generate")
async def generate_google_maps_leads(
    lead_form_id: str,
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Generate leads from Google Maps/Places API

    Uses intelligent API selection (Text Search or Nearby Search) based on form parameters
    """
    try:
        print(f"\n🗺️ [API] Google Maps lead generation request:")
        print(f"   Lead Form ID: {lead_form_id}")
        print(f"   User ID: {user_id}")

        # Get lead form
        lead_form = await LeadFormRepository.get_by_id(db, lead_form_id)

        if not lead_form:
            return UriResponse.error_response(
                message="Lead form not found",
                error_code=404
            )

        if lead_form.get("form_type") != LeadFormTypeEnum.GOOGLE_MAPS.value:
            return UriResponse.error_response(
                message="Invalid form type. Must be GOOGLE_MAPS.",
                error_code=400
            )

        # Import here to avoid circular dependency
        from app.services.LeadService import LeadService

        # Generate leads
        result = await LeadService.generate_google_maps_leads(lead_form, db)

        return result

    except Exception as e:
        print(f"\n❌ ERROR generating Google Maps leads:")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        import traceback
        traceback.print_exc()

        return UriResponse.error_response(
            message=f"Failed to generate Google Maps leads: {str(e)}",
            error_code=500
        )


@router.post("/conversation-search/create")
async def create_conversational_lead_form(
    data: ConversationalSearchFormInput,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    try:
        print(f"📥 Received conversational form data: {data.model_dump()}")
        payload = LeadFormCreate(**data.model_dump())
        result = await LeadFormService.create(db, payload, background_tasks)

        return UriResponse.get_status_response(
            response=jsonable_encoder(result), status_code=result["responseCode"]
        )
    except Exception as e:
        print(f"❌ Validation error creating conversational form: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


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

    # Check credits for Sales Signal scan (7 credits per scan)
    from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService

    try:
        credit_check = await UriTaskManagerService.check_payment_balance(
            user_id=user_id,
            action_type="SALES_SIGNAL_SCAN",
            payment_mode="CREDITS",
            quantity=1
        )

        if credit_check.get("status") and credit_check.get("responseData"):
            balance_data = credit_check["responseData"]
            if not balance_data.get("hasSufficientBalance"):
                return UriResponse.get_status_response(
                    response={
                        "message": "Insufficient credits for sales signal scan. Requires 7 credits.",
                        "required_credits": balance_data.get("requiredAmount", 7),
                        "available_credits": balance_data.get("availableBalance", 0),
                        "limit_exceeded": True
                    },
                    status_code=403
                )
    except Exception as e:
        print(f"⚠️ Credit check failed: {str(e)}")
        # Continue anyway if credit check fails (for backward compatibility)

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


@router.post("/conversation-search/job-status/{job_id}/cancel")
async def cancel_lead_generation_job(
    job_id: str,
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Cancel a running lead generation job.

    **Behavior**:
    - Queued jobs: Immediately cancelled (not yet started)
    - Processing jobs: Worker will stop gracefully at next checkpoint
    - Completed/Failed jobs: Returns current stats (no action)

    **Response**:
    - 200: Cancellation requested successfully
    - 403: Job belongs to different user
    - 404: Job not found

    **Partial Results**:
    - Frontend should continue polling job status
    - When status becomes "cancelled", stats contain partial results
    - Stats include: posts_fetched, posts_analyzed, leads_saved
    """
    from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository

    try:
        # 1. Verify job exists and belongs to user
        job = await LeadGenerationJobRepository.get_job_status(db, job_id)

        if not job:
            return UriResponse.get_error_response(
                "Job not found",
                404
            )

        if job["user_id"] != user_id:
            return UriResponse.get_error_response(
                "You don't have permission to cancel this job",
                403
            )

        current_status = job.get("status")

        # 2. Check if job is cancellable
        if current_status in ["completed", "failed"]:
            return UriResponse.get_single_data_response(
                "Job already finished",
                {
                    "job_id": job_id,
                    "status": current_status,
                    "message": "Job has already completed. No cancellation needed.",
                    "stats": job.get("stats", {})
                }
            )

        if current_status == "cancelled":
            return UriResponse.get_single_data_response(
                "Job already cancelled",
                {
                    "job_id": job_id,
                    "status": "cancelled",
                    "message": "Job was already cancelled.",
                    "stats": job.get("stats", {})
                }
            )

        if current_status == "cancelling":
            # Check if job has been cancelling for too long (> 5 seconds)
            from datetime import datetime, timedelta
            cancellation_requested_at = job.get("cancellation_requested_at")
            if cancellation_requested_at:
                time_since_cancellation = datetime.utcnow() - cancellation_requested_at
                if time_since_cancellation > timedelta(seconds=5):
                    # Force cancel - worker likely crashed or never picked up
                    print(f"⚠️ Force-cancelling job {job_id} (stuck in cancelling for {time_since_cancellation.seconds}s)")
                    await LeadGenerationJobRepository.mark_cancelled(
                        db=db,
                        job_id=job_id,
                        partial_stats=job.get("stats", {}),
                        processed_count=job.get("progress", 0)
                    )
                    return UriResponse.get_single_data_response(
                        "Job cancelled (force stopped)",
                        {
                            "job_id": job_id,
                            "status": "cancelled",
                            "message": "Job was force-cancelled after timeout",
                            "stats": job.get("stats", {})
                        }
                    )

            return UriResponse.get_single_data_response(
                "Cancellation in progress",
                {
                    "job_id": job_id,
                    "status": "cancelling",
                    "message": "Cancellation already in progress. Worker will stop shortly.",
                    "current_progress": job.get("progress", 0)
                }
            )

        # 3. Request cancellation
        cancellation_accepted = await LeadGenerationJobRepository.mark_cancellation_requested(
            db=db,
            job_id=job_id
        )

        if not cancellation_accepted:
            return UriResponse.get_error_response(
                "Could not cancel job. It may have just completed.",
                409
            )

        # 4. Success response
        return UriResponse.get_single_data_response(
            "Cancellation requested successfully",
            {
                "job_id": job_id,
                "status": "cancelling",
                "message": "Worker will stop at next checkpoint (5-15 seconds). Continue polling for final stats.",
                "estimated_stop_time": "5-15 seconds",
                "current_progress": job.get("progress", 0),
                "note": "Partial results will be available when status becomes 'cancelled'"
            }
        )

    except Exception as e:
        print(f"❌ Error cancelling job {job_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.get_error_response(
            f"Failed to cancel job: {str(e)}",
            500
        )


@router.post("/conversation-search/job-status/{job_id}/force-cancel")
async def force_cancel_job(
    job_id: str,
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    FORCE-CANCEL a job immediately without waiting for worker.
    Use this when job is stuck and won't respond to normal cancellation.
    """
    from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository

    try:
        # Verify job exists and belongs to user
        job = await LeadGenerationJobRepository.get_job_status(db, job_id)

        if not job:
            return UriResponse.get_error_response("Job not found", 404)

        if job["user_id"] != user_id:
            return UriResponse.get_error_response(
                "You don't have permission to cancel this job", 403
            )

        # Force-cancel immediately regardless of status
        await LeadGenerationJobRepository.mark_cancelled(
            db=db,
            job_id=job_id,
            partial_stats=job.get("stats", {}),
            processed_count=job.get("progress", 0)
        )

        print(f"⚡ FORCE-CANCELLED job {job_id} by user request")

        return UriResponse.get_single_data_response(
            "Job force-cancelled successfully",
            {
                "job_id": job_id,
                "status": "cancelled",
                "message": "Job was force-cancelled immediately",
                "stats": job.get("stats", {})
            }
        )

    except Exception as e:
        print(f"❌ Error force-cancelling job {job_id}: {str(e)}")
        return UriResponse.get_error_response(
            f"Failed to force-cancel job: {str(e)}", 500
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


@router.put("/google-maps-search/update")
async def update_google_maps_lead_form(
    lead_form_id: str,
    data: GoogleMapsLeadFormUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    result = await LeadFormService.update_google_maps_lead_form(
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


# ========== Multi-Form Support Endpoints (PRD Section 4.1) ==========

@router.get("/getByUserAndType")
async def get_forms_by_user_and_type(
    user_id: str,
    form_type: LeadFormTypeEnum,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get all lead forms for a specific user and form type.
    Supports multiple forms per user per type (PRD 4.1).
    """
    forms = await LeadFormRepository.get_forms_by_user_and_type(db, user_id, form_type)

    return UriResponse.get_status_response(
        response=jsonable_encoder(UriResponse.get_list_data_response("Lead forms", forms)),
        status_code=200
    )


@router.post("/setDefault")
async def set_default_form(
    user_id: str,
    form_type: LeadFormTypeEnum,
    lead_form_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Mark a specific form as the default for a user and form type.
    All other forms of the same type will be unmarked as default.
    """
    result = await LeadFormRepository.set_default_form(db, user_id, form_type, lead_form_id)

    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result.get("responseCode", 200)
    )


@router.get("/getDefault")
async def get_default_form(
    user_id: str,
    form_type: LeadFormTypeEnum,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get the default form for a user and form type.
    Falls back to most recent form if no default is set.
    """
    result = await LeadFormRepository.get_default_form(db, user_id, form_type)

    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result.get("responseCode", 200)
    )


@router.patch("/toggle-pause/{lead_form_id}")
async def toggle_pause_form(
    lead_form_id: str,
    disabled: bool,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Toggle pause/resume for a lead form.
    When paused (disabled=True), form stops auto-generating leads.

    Args:
        lead_form_id: ID of the form to toggle
        disabled: True to pause, False to resume

    Returns:
        Success response with updated form
    """
    result = await LeadFormRepository.update(
        db,
        lead_form_id,
        LeadFormUpdateBase(
            disabled=disabled,
            disabled_reason="User paused" if disabled else None
        )
    )

    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result.get("responseCode", 200)
    )


@router.patch("/toggle-auto-generate/{lead_form_id}")
async def toggle_auto_generate(
    lead_form_id: str,
    auto_generate: bool,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Toggle auto-generate for a lead form.
    When enabled, form automatically generates leads on schedule.

    Args:
        lead_form_id: ID of the form to toggle
        auto_generate: True to enable, False to disable

    Returns:
        Success response with updated form
    """
    result = await LeadFormRepository.update(
        db,
        lead_form_id,
        LeadFormUpdateBase(auto_generate=auto_generate)
    )

    return UriResponse.get_status_response(
        response=jsonable_encoder(result),
        status_code=result.get("responseCode", 200)
    )
