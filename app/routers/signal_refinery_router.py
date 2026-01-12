"""
Signal Refinery Router - API endpoints for X-Ray testing system

Endpoints:
- POST /search - Start X-Ray search
- GET /jobs/{job_id} - Get job status
- GET /jobs - List user's jobs
- GET /leads - Get refined leads
- GET /metrics - Get performance metrics
- POST /preview-query - Preview dork queries
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
import asyncio
import logging

from app.database import get_db
from app.dependencies import get_db_dependency
from app.domain.schemas.signal_refinery_schema import (
    XRaySearchRequest,
    XRaySearchResponse,
    XRayJobStatusResponse,
    XRaySearchJob,
    XRayLead,
    DorkQueryPreview,
    XRayPlatformEnum
)
from app.repository.SignalRefineryRepository import SignalRefineryRepository
from app.services.ApifyGoogleSearchService import ApifyGoogleSearchService
from app.services.SignalRefineryService import SignalRefineryService
from app.domain.responses.uri_response import UriResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Signal Refinery (X-Ray Test)"])

# Log at module load time to verify code is being loaded
logger.info("=" * 80)
logger.info("🔥 SIGNAL REFINERY ROUTER MODULE LOADED - CODE IS ACTIVE 🔥")
logger.info("=" * 80)


# ========================================
# BACKGROUND JOB PROCESSOR
# ========================================

async def process_xray_search_job(
    job_id: str,
    user_id: str,
    request: XRaySearchRequest,
    db: AsyncIOMotorDatabase
):
    """
    Background task to process X-Ray search

    Pipeline:
    1. Build dork queries for each platform
    2. Execute Google searches
    3. Run Signal Refinery (filter + classify)
    4. Save leads and metrics
    """
    logger.info(f"🎬 BACKGROUND TASK STARTED for job {job_id}")
    try:
        logger.info(f"🚀 Starting X-Ray search job: {job_id}")

        google_service = ApifyGoogleSearchService()
        refinery_service = SignalRefineryService()

        # Update job status
        await SignalRefineryRepository.update_job_progress(
            db, job_id, 10, "Building dork queries...", "running"
        )

        # STEP 1: Execute Google searches for each platform
        await SignalRefineryRepository.update_job_progress(
            db, job_id, 20, f"Searching {len(request.platforms)} platforms..."
        )

        all_results = []
        for idx, platform in enumerate(request.platforms):
            platform_progress = 20 + (30 * (idx + 1) // len(request.platforms))
            await SignalRefineryRepository.update_job_progress(
                db, job_id, platform_progress, f"Searching {platform.value}..."
            )

            # Build dork query
            dork_query = google_service.build_dork_query(
                platform=platform,
                keyword=request.keyword,
                location=request.location
            )
            logger.info(f"🔍 Executing search for {platform.value} with query: {dork_query}")

            # Execute search
            results = await google_service.search(
                dork_query=dork_query,
                max_results=request.max_results_per_platform
            )

            logger.info(f"   ✅ {platform.value}: {len(results)} results returned from search()")
            all_results.extend(results)

        total_results = len(all_results)
        logger.info(f"📊 Total results from Google: {total_results}")

        # STEP 2: Run Signal Refinery
        await SignalRefineryRepository.update_job_progress(
            db, job_id, 60, "Running Signal Refinery filters..."
        )

        leads, filtered, metrics = await refinery_service.refine_signals(
            results=all_results,
            user_id=user_id,
            search_keyword=request.keyword,
            location=request.location,
            enable_buyer_seller_classification=request.enable_buyer_seller_classification,
            enable_nigerian_filter=request.enable_nigerian_filter
        )

        logger.info(f"✅ Refinery complete: {len(leads)} buyer leads")

        # STEP 3: Save leads
        await SignalRefineryRepository.update_job_progress(
            db, job_id, 90, "Saving leads..."
        )

        if leads:
            await SignalRefineryRepository.save_leads(db, leads)

        # STEP 4: Complete job
        await SignalRefineryRepository.update_job_progress(
            db, job_id, 95, "Finalizing..."
        )

        # Convert results and filtered to dicts for storage
        results_dicts = [r.dict() for r in all_results]
        filtered_dicts = [f.dict() for f in filtered]

        await SignalRefineryRepository.complete_job(
            db=db,
            job_id=job_id,
            leads=leads,
            metrics=metrics,
            results=results_dicts,
            filtered=filtered_dicts
        )

        logger.info(f"✅ Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"❌ Error processing X-Ray job {job_id}: {str(e)}")
        import traceback
        traceback.print_exc()

        await SignalRefineryRepository.fail_job(
            db=db,
            job_id=job_id,
            error_message=str(e)
        )


# ========================================
# API ENDPOINTS
# ========================================

@router.post("/search", response_model=dict)
async def start_xray_search(
    request: XRaySearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Start X-Ray search job

    This runs in the background and returns immediately with job_id.
    Poll /jobs/{job_id} to check progress.
    """
    try:
        user_id = request.user_id

        # Create job
        job_id = await SignalRefineryRepository.create_job(
            db=db,
            user_id=user_id,
            request=request
        )

        logger.info(f"🚀 Created X-Ray search job {job_id} for user {user_id}")

        # Start background task
        background_tasks.add_task(
            process_xray_search_job,
            job_id=job_id,
            user_id=user_id,
            request=request,
            db=db
        )

        return UriResponse.get_single_data_response(
            entity_name="X-Ray Search Job",
            data={
                "job_id": job_id,
                "status": "running",
                "keyword": request.keyword,
                "platforms": [p.value for p in request.platforms]
            },
            message="X-Ray search started"
        )

    except Exception as e:
        logger.error(f"❌ Error starting X-Ray search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=dict)
async def get_job_status(
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get status of X-Ray search job"""
    try:
        job = await SignalRefineryRepository.get_job(db, job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return UriResponse.get_single_data_response(
            entity_name="X-Ray Search Job",
            data=job.dict(),
            message=f"Job status: {job.status}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=dict)
async def list_jobs(
    user_id: str = Query(...),
    skip: int = 0,
    limit: int = 20,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """List all X-Ray search jobs for user"""
    try:

        jobs = await SignalRefineryRepository.get_jobs_by_user(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit
        )

        jobs_data = [job.dict() for job in jobs]

        return UriResponse.get_list_data_response(
            entity_name="X-Ray Search Jobs",
            data=jobs_data,
            message=f"Found {len(jobs)} jobs"
        )

    except Exception as e:
        logger.error(f"❌ Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leads", response_model=dict)
async def get_refined_leads(
    user_id: str = Query(...),
    skip: int = 0,
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get all refined leads (buyers only)"""
    try:

        leads = await SignalRefineryRepository.get_leads_by_user(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit
        )

        leads_data = [lead.dict() for lead in leads]

        return UriResponse.get_list_data_response(
            entity_name="Refined Leads",
            data=leads_data,
            message=f"Found {len(leads)} refined leads"
        )

    except Exception as e:
        logger.error(f"❌ Error getting leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=dict)
async def get_metrics_summary(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get aggregate metrics across all jobs"""
    try:

        metrics = await SignalRefineryRepository.get_metrics_summary(
            db=db,
            user_id=user_id
        )

        return UriResponse.get_single_data_response(
            entity_name="Metrics Summary",
            data=metrics,
            message="Metrics summary"
        )

    except Exception as e:
        logger.error(f"❌ Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-query", response_model=dict)
async def preview_dork_queries(
    keyword: str = Query(...),
    platforms: List[XRayPlatformEnum] = Query(...),
    location: str = Query("Nigeria"),
):
    """
    Preview dork queries that will be used (without executing search)

    Useful for frontend to show user what queries will run
    """
    try:
        previews = ApifyGoogleSearchService.preview_dork_queries(
            keyword=keyword,
            platforms=platforms,
            location=location
        )

        previews_data = [p.dict() for p in previews]

        return UriResponse.get_list_data_response(
            entity_name="Dork Query Previews",
            data=previews_data,
            message=f"Generated {len(previews)} dork queries"
        )

    except Exception as e:
        logger.error(f"❌ Error previewing queries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}", response_model=dict)
async def delete_job(
    job_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Delete a job (cleanup)"""
    try:

        deleted = await SignalRefineryRepository.delete_job(
            db=db,
            job_id=job_id,
            user_id=user_id
        )

        if deleted:
            return UriResponse.get_single_data_response(
                entity_name="X-Ray Search Job",
                data={"job_id": job_id},
                message="Job deleted"
            )
        else:
            raise HTTPException(status_code=404, detail="Job not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
