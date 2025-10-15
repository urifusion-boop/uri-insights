"""
Twitter Monitoring API Router
Endpoints for controlling Playwright-based Twitter monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.services.TwitterMonitoringOrchestrator import TwitterMonitoringOrchestrator
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global orchestrator instance (will be initialized on first use)
_orchestrator: Optional[TwitterMonitoringOrchestrator] = None


class StartMonitoringRequest(BaseModel):
    """Request to start Twitter monitoring for a lead form."""
    lead_form_id: str
    poll_interval: Optional[int] = 60  # seconds


class MonitoringStatusResponse(BaseModel):
    """Response with monitoring task status."""
    task_id: str
    lead_form_id: str
    user_id: str
    is_running: bool
    created_at: str
    last_run: Optional[str]
    tweets_processed: int
    leads_generated: int
    poll_interval: int


async def get_orchestrator(db: AsyncIOMotorDatabase) -> TwitterMonitoringOrchestrator:
    """Get or initialize the global orchestrator instance."""
    global _orchestrator

    if _orchestrator is None:
        logger.info("Initializing Twitter Monitoring Orchestrator...")
        _orchestrator = TwitterMonitoringOrchestrator(db)

        # Initialize with Twitter credentials from settings
        twitter_username = getattr(settings, 'TWITTER_USERNAME', None)
        twitter_password = getattr(settings, 'TWITTER_PASSWORD', None)

        if not twitter_username or not twitter_password:
            raise HTTPException(
                status_code=500,
                detail="Twitter credentials not configured. Please set TWITTER_USERNAME and TWITTER_PASSWORD in .env"
            )

        try:
            await _orchestrator.initialize(twitter_username, twitter_password)
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            _orchestrator = None
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Twitter monitoring: {str(e)}"
            )

    return _orchestrator


@router.post("/start")
async def start_twitter_monitoring(
    request: StartMonitoringRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Start Twitter monitoring for a specific lead form.

    This will continuously monitor Twitter for tweets matching the lead form's
    keywords and buying signals, and generate leads in real-time.
    """
    try:
        orchestrator = await get_orchestrator(db)

        task_id = await orchestrator.start_monitoring_for_lead_form(
            request.lead_form_id
        )

        return {
            "status": "success",
            "message": f"Twitter monitoring started for lead form {request.lead_form_id}",
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start monitoring: {str(e)}"
        )


@router.post("/stop/{task_id}")
async def stop_twitter_monitoring(
    task_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Stop a specific Twitter monitoring task."""
    try:
        orchestrator = await get_orchestrator(db)

        success = await orchestrator.stop_monitoring_task(task_id)

        if success:
            return {
                "status": "success",
                "message": f"Monitoring task {task_id} stopped"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop monitoring: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=MonitoringStatusResponse)
async def get_monitoring_status(
    task_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get status of a specific monitoring task."""
    try:
        orchestrator = await get_orchestrator(db)

        status = await orchestrator.get_task_status(task_id)

        if status:
            return status
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/status", response_model=List[MonitoringStatusResponse])
async def get_all_monitoring_status(
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get status of all active monitoring tasks."""
    try:
        orchestrator = await get_orchestrator(db)

        statuses = await orchestrator.get_all_tasks_status()

        return statuses

    except Exception as e:
        logger.error(f"Error getting all statuses: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statuses: {str(e)}"
        )


@router.post("/stop-all")
async def stop_all_monitoring(
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Stop all active Twitter monitoring tasks."""
    try:
        orchestrator = await get_orchestrator(db)

        statuses = await orchestrator.get_all_tasks_status()
        stopped_count = 0

        for status in statuses:
            success = await orchestrator.stop_monitoring_task(status["task_id"])
            if success:
                stopped_count += 1

        return {
            "status": "success",
            "message": f"Stopped {stopped_count} monitoring tasks"
        }

    except Exception as e:
        logger.error(f"Error stopping all monitoring: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop all monitoring: {str(e)}"
        )


@router.get("/health")
async def monitoring_health_check(
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Check health of Twitter monitoring system."""
    try:
        if _orchestrator is None:
            return {
                "status": "not_initialized",
                "message": "Twitter monitoring orchestrator not initialized"
            }

        is_initialized = _orchestrator.is_initialized

        return {
            "status": "healthy" if is_initialized else "unhealthy",
            "is_initialized": is_initialized,
            "active_tasks": len(_orchestrator.active_tasks)
        }

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
