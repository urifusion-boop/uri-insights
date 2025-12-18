"""
Admin Lead Analytics Router

Provides aggregated lead analytics for admin dashboard.
Separate from user-facing endpoints to maintain security and performance.
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
from fastapi.encoders import jsonable_encoder

from app.dependencies import get_db_dependency
from app.domain.responses.uri_response import UriResponse
from app.services.admin.AdminLeadAnalyticsService import AdminLeadAnalyticsService
from app.domain.enums.date_enum import DateFilterEnum


router = APIRouter(prefix="/admin/leads", tags=["Admin Lead Analytics"])


@router.get("/overview")
async def get_lead_overview(
    date_filter: DateFilterEnum = Query(DateFilterEnum.LAST_1_MONTH),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get overview of all leads across all users.

    Returns:
    - Total leads count
    - Leads by status (new, contacted, qualified, unqualified, converted)
    - Leads by platform (Twitter, Facebook, TikTok)
    - Top performing users by lead count
    - Conversion metrics
    """
    data = await AdminLeadAnalyticsService.get_lead_overview(db, date_filter)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/by-user/{user_id}")
async def get_user_lead_analytics(
    user_id: str,
    date_filter: DateFilterEnum = Query(DateFilterEnum.LAST_1_MONTH),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get detailed lead analytics for a specific user.

    Returns:
    - Lead counts by status
    - Lead sources breakdown
    - Leads by industry
    - Interest level distribution
    - Platform breakdown
    """
    data = await AdminLeadAnalyticsService.get_user_lead_analytics(db, user_id, date_filter)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/recent")
async def get_recent_leads_all_users(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    status: Optional[str] = None,
    platform: Optional[str] = None,
    user_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get recent leads across all users with filtering options.
    Supports pagination, filtering by status, platform, and user.
    """
    data = await AdminLeadAnalyticsService.get_recent_leads_paginated(
        db, limit, skip, status, platform, user_id
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/top-users")
async def get_top_users_by_leads(
    date_filter: DateFilterEnum = Query(DateFilterEnum.LAST_1_MONTH),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get top users ranked by lead generation metrics.

    Returns list of users with:
    - Total leads count
    - Qualified leads count
    - Converted leads count
    - Conversion rate
    """
    data = await AdminLeadAnalyticsService.get_top_users_by_leads(db, date_filter, limit)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/trends")
async def get_lead_generation_trends(
    days: int = Query(30, ge=7, le=90),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get daily lead generation trends for the specified number of days.

    Returns time-series data showing:
    - Daily lead counts
    - Leads by status over time
    - Platform distribution over time
    """
    data = await AdminLeadAnalyticsService.get_lead_trends(db, days)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/conversion-funnel")
async def get_conversion_funnel(
    date_filter: DateFilterEnum = Query(DateFilterEnum.LAST_1_MONTH),
    user_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get conversion funnel analytics.

    Shows progression through stages:
    - New leads
    - Contacted
    - Qualified
    - Converted

    Includes conversion rates at each stage.
    """
    data = await AdminLeadAnalyticsService.get_conversion_funnel(db, date_filter, user_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/platform-performance")
async def get_platform_performance(
    date_filter: DateFilterEnum = Query(DateFilterEnum.LAST_1_MONTH),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get performance metrics by platform (Twitter, Facebook, TikTok).

    Returns for each platform:
    - Total leads
    - Average intent score
    - Average relevance score
    - Conversion rate
    """
    data = await AdminLeadAnalyticsService.get_platform_performance(db, date_filter)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
