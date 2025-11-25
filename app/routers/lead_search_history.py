"""
Lead Search History Router
API endpoints for managing and retrieving lead search history
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies import get_db_dependency
from app.repository.LeadSearchHistoryRepository import LeadSearchHistoryRepository
from app.domain.responses.uri_response import UriResponse

router = APIRouter(
    prefix="/lead-search-history",
    tags=["Lead Search History"]
)


@router.get("/user/{user_id}")
async def get_user_search_history(
    user_id: str,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get search history for a user

    Args:
        user_id: User ID
        limit: Maximum number of records to return (default 50, max 200)
        skip: Number of records to skip for pagination
    """
    return await LeadSearchHistoryRepository.get_by_user(db, user_id, limit, skip)


@router.get("/lead-form/{lead_form_id}")
async def get_lead_form_search_history(
    lead_form_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get search history for a specific lead form

    Args:
        lead_form_id: Lead form ID
        limit: Maximum number of records to return (default 50, max 200)
    """
    return await LeadSearchHistoryRepository.get_by_lead_form(db, lead_form_id, limit)


@router.get("/lead-form/{lead_form_id}/summary")
async def get_lead_form_search_summary(
    lead_form_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get summary statistics for a lead form's search history

    Returns aggregated data like:
    - Total number of searches
    - Total leads found
    - Total duplicates skipped
    - Last search timestamp
    - Most used keyword
    - Average leads per search
    """
    return await LeadSearchHistoryRepository.get_summary(db, lead_form_id)


@router.get("/lead-form/{lead_form_id}/recent")
async def check_recent_search(
    lead_form_id: str,
    keyword: str = Query(..., description="Keyword to check"),
    hours: int = Query(1, ge=1, le=24, description="Check within last N hours"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Check if the same search was run recently for a lead form

    Useful for preventing duplicate searches too frequently

    Args:
        lead_form_id: Lead form ID
        keyword: Keyword to check
        hours: Time window in hours (default 1, max 24)
    """
    recent_search = await LeadSearchHistoryRepository.get_recent_search(
        db, lead_form_id, keyword, hours
    )

    if recent_search:
        return UriResponse.get_status_response(
            response={
                "status": True,
                "responseCode": 200,
                "responseMessage": f"Same search was run {hours} hour(s) ago",
                "responseData": {
                    "found": True,
                    "search": recent_search.dict()
                }
            },
            status_code=200
        )
    else:
        return UriResponse.get_status_response(
            response={
                "status": True,
                "responseCode": 200,
                "responseMessage": "No recent search found",
                "responseData": {
                    "found": False
                }
            },
            status_code=200
        )


@router.post("/cleanup")
async def cleanup_old_history(
    days: int = Query(90, ge=30, le=365, description="Delete records older than N days"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Delete search history older than specified days

    Args:
        days: Delete records older than this many days (default 90, min 30, max 365)
    """
    deleted_count = await LeadSearchHistoryRepository.delete_old_history(db, days)

    return UriResponse.get_status_response(
        response={
            "status": True,
            "responseCode": 200,
            "responseMessage": f"Deleted {deleted_count} old search history records",
            "responseData": {"deleted_count": deleted_count}
        },
        status_code=200
    )
