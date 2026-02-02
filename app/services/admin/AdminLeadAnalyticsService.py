"""
Admin Lead Analytics Service

Provides aggregated analytics for admin dashboard using MongoDB aggregation pipelines.
All queries are optimized for performance with proper indexing considerations.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId

from app.domain.enums.date_enum import DateFilterEnum
from app.repository.admin.AdminLeadAnalyticsRepository import AdminLeadAnalyticsRepository


class AdminLeadAnalyticsService:
    """Service layer for admin lead analytics with business logic"""

    @staticmethod
    def _get_date_range(date_filter: DateFilterEnum) -> Dict[str, datetime]:
        """Convert date filter enum to actual date range"""
        now = datetime.utcnow()

        date_ranges = {
            DateFilterEnum.LAST_24_HOURS: timedelta(days=1),
            DateFilterEnum.LAST_3_DAYS: timedelta(days=3),
            DateFilterEnum.LAST_7_DAYS: timedelta(days=7),
            DateFilterEnum.LAST_1_WEEK: timedelta(days=7),
            DateFilterEnum.LAST_2_WEEKS: timedelta(days=14),
            DateFilterEnum.LAST_1_MONTH: timedelta(days=30),
            DateFilterEnum.LAST_2_MONTHS: timedelta(days=60),
            DateFilterEnum.LAST_3_MONTHS: timedelta(days=90),
        }

        delta = date_ranges.get(date_filter, timedelta(days=30))
        start_date = now - delta

        return {
            "start_date": start_date,
            "end_date": now
        }

    @staticmethod
    async def get_lead_overview(
        db: AsyncIOMotorDatabase,
        date_filter: DateFilterEnum
    ) -> Dict[str, Any]:
        """
        Get comprehensive lead overview across all users
        """
        date_range = AdminLeadAnalyticsService._get_date_range(date_filter)

        # Get all aggregated metrics in parallel
        total_count = await AdminLeadAnalyticsRepository.get_total_leads_count(
            db, date_range["start_date"], date_range["end_date"]
        )

        status_breakdown = await AdminLeadAnalyticsRepository.get_leads_by_status(
            db, date_range["start_date"], date_range["end_date"]
        )

        platform_breakdown = await AdminLeadAnalyticsRepository.get_leads_by_platform(
            db, date_range["start_date"], date_range["end_date"]
        )

        top_users = await AdminLeadAnalyticsRepository.get_top_users_by_lead_count(
            db, date_range["start_date"], date_range["end_date"], limit=10
        )

        conversion_metrics = await AdminLeadAnalyticsRepository.get_conversion_metrics(
            db, date_range["start_date"], date_range["end_date"]
        )

        return {
            "status": True,
            "responseCode": 200,
            "responseMessage": "Lead overview retrieved successfully",
            "responseData": {
                "total_leads": total_count,
                "status_breakdown": status_breakdown,
                "platform_breakdown": platform_breakdown,
                "top_users": top_users,
                "conversion_metrics": conversion_metrics,
                "date_range": {
                    "start": date_range["start_date"].isoformat(),
                    "end": date_range["end_date"].isoformat(),
                    "filter": date_filter.value
                }
            }
        }

    @staticmethod
    async def get_user_lead_analytics(
        db: AsyncIOMotorDatabase,
        user_id: str,
        date_filter: DateFilterEnum
    ) -> Dict[str, Any]:
        """
        Get detailed analytics for a specific user's leads
        """
        date_range = AdminLeadAnalyticsService._get_date_range(date_filter)

        # Validate user_id format
        if not ObjectId.is_valid(user_id):
            return {
                "status": False,
                "responseCode": 400,
                "responseMessage": "Invalid user_id format",
                "responseData": None
            }

        user_stats = await AdminLeadAnalyticsRepository.get_user_lead_statistics(
            db, user_id, date_range["start_date"], date_range["end_date"]
        )

        if not user_stats:
            return {
                "status": True,
                "responseCode": 200,
                "responseMessage": "No leads found for this user",
                "responseData": {
                    "new_leads": 0,
                    "contacted": 0,
                    "qualified": 0,
                    "unqualified": 0,
                    "converted": 0,
                    "lead_sources_breakdown": {},
                    "leads_by_industry": {},
                    "interest_by_platform": {}
                }
            }

        return {
            "status": True,
            "responseCode": 200,
            "responseMessage": f"Lead analytics for user {user_id} retrieved successfully",
            "responseData": user_stats
        }

    @staticmethod
    async def get_recent_leads_paginated(
        db: AsyncIOMotorDatabase,
        limit: int,
        skip: int,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get recent leads with pagination and filters
        """
        # Validate user_id if provided
        if user_id and not ObjectId.is_valid(user_id):
            return {
                "status": False,
                "responseCode": 400,
                "responseMessage": "Invalid user_id format",
                "responseData": None
            }

        leads = await AdminLeadAnalyticsRepository.get_recent_leads(
            db, limit, skip, status, platform, user_id
        )

        total = await AdminLeadAnalyticsRepository.count_leads_with_filters(
            db, status, platform, user_id
        )

        return {
            "status": True,
            "responseCode": 200,
            "responseMessage": "Recent leads retrieved successfully",
            "responseData": {
                "leads": leads,
                "total": total,
                "page": (skip // limit) + 1 if limit > 0 else 1,
                "page_size": limit,
                "has_more": (skip + len(leads)) < total
            }
        }

    @staticmethod
    async def get_top_users_by_leads(
        db: AsyncIOMotorDatabase,
        date_filter: DateFilterEnum,
        limit: int
    ) -> Dict[str, Any]:
        """
        Get top users ranked by lead generation metrics
        """
        date_range = AdminLeadAnalyticsService._get_date_range(date_filter)

        top_users = await AdminLeadAnalyticsRepository.get_top_users_with_metrics(
            db, date_range["start_date"], date_range["end_date"], limit
        )

        return {
            "status": True,
            "responseCode": 200,
            "responseMessage": f"Top {limit} users retrieved successfully",
            "responseData": {
                "users": top_users,
                "count": len(top_users)
            }
        }

    @staticmethod
    async def get_lead_trends(
        db: AsyncIOMotorDatabase,
        days: int
    ) -> Dict[str, Any]:
        """
        Get time-series data for lead generation trends
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        daily_trends = await AdminLeadAnalyticsRepository.get_daily_lead_trends(
            db, start_date, end_date
        )

        return {
            "status": True,
            "responseCode": 200,
            "responseMessage": f"Lead trends for last {days} days retrieved successfully",
            "responseData": {
                "trends": daily_trends,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days
                }
            }
        }

    @staticmethod
    async def get_conversion_funnel(
        db: AsyncIOMotorDatabase,
        date_filter: DateFilterEnum,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get conversion funnel with stage progression rates
        """
        date_range = AdminLeadAnalyticsService._get_date_range(date_filter)

        # Validate user_id if provided
        if user_id and not ObjectId.is_valid(user_id):
            return {
                "status": False,
                "responseCode": 400,
                "responseMessage": "Invalid user_id format",
                "responseData": None
            }

        funnel_data = await AdminLeadAnalyticsRepository.get_conversion_funnel_data(
            db, date_range["start_date"], date_range["end_date"], user_id
        )

        return {
            "status": True,
            "responseCode": 200,
            "responseMessage": "Conversion funnel retrieved successfully",
            "responseData": funnel_data
        }

    @staticmethod
    async def get_platform_performance(
        db: AsyncIOMotorDatabase,
        date_filter: DateFilterEnum
    ) -> Dict[str, Any]:
        """
        Get performance metrics by platform with quality scores
        """
        date_range = AdminLeadAnalyticsService._get_date_range(date_filter)

        platform_metrics = await AdminLeadAnalyticsRepository.get_platform_metrics(
            db, date_range["start_date"], date_range["end_date"]
        )

        return {
            "status": True,
            "responseCode": 200,
            "responseMessage": "Platform performance metrics retrieved successfully",
            "responseData": {
                "platforms": platform_metrics,
                "date_range": {
                    "start": date_range["start_date"].isoformat(),
                    "end": date_range["end_date"].isoformat()
                }
            }
        }

    @staticmethod
    async def get_lead_type_distribution(
        db: AsyncIOMotorDatabase,
        date_filter: DateFilterEnum
    ) -> Dict[str, Any]:
        """
        Get lead distribution and analytics by lead type
        """
        date_range = AdminLeadAnalyticsService._get_date_range(date_filter)

        type_metrics = await AdminLeadAnalyticsRepository.get_lead_type_distribution(
            db, date_range["start_date"], date_range["end_date"]
        )

        return {
            "status": True,
            "responseCode": 200,
            "responseMessage": "Lead type distribution retrieved successfully",
            "responseData": {
                "lead_types": type_metrics,
                "date_range": {
                    "start": date_range["start_date"].isoformat(),
                    "end": date_range["end_date"].isoformat()
                }
            }
        }
