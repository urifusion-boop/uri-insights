"""
Admin Lead Analytics Repository

MongoDB aggregation pipelines for admin lead analytics.
Optimized queries using proper indexing and aggregation framework.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId


class AdminLeadAnalyticsRepository:
    """Repository for admin lead analytics with MongoDB aggregations"""

    LEADS_COLLECTION = "leads"
    USERS_COLLECTION = "users"

    @staticmethod
    async def get_total_leads_count(
        db: AsyncIOMotorDatabase,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """Get total count of leads within date range"""
        # Debug: Check what date field exists in leads
        sample_lead = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].find_one()
        print(f"[DEBUG] Sample lead fields: {sample_lead.keys() if sample_lead else 'No leads found'}")
        print(f"[DEBUG] Date range: {start_date} to {end_date}")

        # Try both created_date and created_at fields
        count_created_date = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].count_documents({
            "created_date": {"$gte": start_date, "$lte": end_date}
        })
        count_created_at = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].count_documents({
            "created_at": {"$gte": start_date, "$lte": end_date}
        })
        total_count = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].count_documents({})

        print(f"[DEBUG] Count with created_date: {count_created_date}")
        print(f"[DEBUG] Count with created_at: {count_created_at}")
        print(f"[DEBUG] Total leads (no filter): {total_count}")

        count = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].count_documents({
            "created_date": {"$gte": start_date, "$lte": end_date}
        })
        return count

    @staticmethod
    async def get_leads_by_status(
        db: AsyncIOMotorDatabase,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """Aggregate leads by status"""
        pipeline = [
            {
                "$match": {
                    "date_created": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)

        # Convert to friendly format
        status_counts = {
            "new": 0,
            "contacted": 0,
            "qualified": 0,
            "unqualified": 0,
            "converted": 0
        }

        for item in result:
            status = item["_id"].lower() if item["_id"] else "new"
            status_counts[status] = item["count"]

        return status_counts

    @staticmethod
    async def get_leads_by_platform(
        db: AsyncIOMotorDatabase,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """Aggregate leads by platform/source"""
        pipeline = [
            {
                "$match": {
                    "date_created": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$lead_source",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)

        platform_counts = {}
        for item in result:
            platform = item["_id"] or "Unknown"
            platform_counts[platform] = item["count"]

        return platform_counts

    @staticmethod
    async def get_top_users_by_lead_count(
        db: AsyncIOMotorDatabase,
        start_date: datetime,
        end_date: datetime,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get top users by lead count"""
        pipeline = [
            {
                "$match": {
                    "date_created": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "lead_count": {"$sum": 1}
                }
            },
            {
                "$sort": {"lead_count": -1}
            },
            {
                "$limit": limit
            },
            {
                "$lookup": {
                    "from": AdminLeadAnalyticsRepository.USERS_COLLECTION,
                    "let": {"userId": {"$toObjectId": "$_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$userId"]}}},
                        {"$project": {"email": 1, "firstName": 1, "lastName": 1}}
                    ],
                    "as": "user_info"
                }
            },
            {
                "$unwind": {
                    "path": "$user_info",
                    "preserveNullAndEmptyArrays": True
                }
            }
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)

        formatted_result = []
        for item in result:
            user_info = item.get("user_info", {})
            formatted_result.append({
                "user_id": item["_id"],
                "email": user_info.get("email", "Unknown"),
                "name": f"{user_info.get('firstName', '')} {user_info.get('lastName', '')}".strip() or "Unknown",
                "lead_count": item["lead_count"]
            })

        return formatted_result

    @staticmethod
    async def get_conversion_metrics(
        db: AsyncIOMotorDatabase,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate conversion metrics"""
        pipeline = [
            {
                "$match": {
                    "date_created": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "qualified": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "qualified"]}, 1, 0]
                        }
                    },
                    "converted": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "converted"]}, 1, 0]
                        }
                    }
                }
            }
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)

        if not result:
            return {
                "total_leads": 0,
                "qualified_leads": 0,
                "converted_leads": 0,
                "qualification_rate": 0.0,
                "conversion_rate": 0.0
            }

        data = result[0]
        total = data["total"]
        qualified = data["qualified"]
        converted = data["converted"]

        return {
            "total_leads": total,
            "qualified_leads": qualified,
            "converted_leads": converted,
            "qualification_rate": round((qualified / total * 100) if total > 0 else 0, 2),
            "conversion_rate": round((converted / qualified * 100) if qualified > 0 else 0, 2)
        }

    @staticmethod
    async def get_user_lead_statistics(
        db: AsyncIOMotorDatabase,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Get comprehensive lead statistics for a specific user"""
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "date_created": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$facet": {
                    "status_breakdown": [
                        {
                            "$group": {
                                "_id": "$status",
                                "count": {"$sum": 1}
                            }
                        }
                    ],
                    "source_breakdown": [
                        {
                            "$group": {
                                "_id": "$lead_source",
                                "count": {"$sum": 1}
                            }
                        }
                    ],
                    "industry_breakdown": [
                        {
                            "$group": {
                                "_id": "$lead_industry_type",
                                "count": {"$sum": 1}
                            }
                        }
                    ],
                    "interest_by_platform": [
                        {
                            "$group": {
                                "_id": {
                                    "platform": "$lead_source",
                                    "interest": "$interest_level"
                                },
                                "count": {"$sum": 1}
                            }
                        }
                    ]
                }
            }
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)

        if not result or not result[0]:
            return None

        data = result[0]

        # Format status breakdown
        status_counts = {"new_leads": 0, "contacted": 0, "qualified": 0, "unqualified": 0, "converted": 0}
        for item in data["status_breakdown"]:
            status = item["_id"].lower() if item["_id"] else "new"
            if status == "new":
                status_counts["new_leads"] = item["count"]
            else:
                status_counts[status] = item["count"]

        # Format source breakdown
        source_breakdown = {}
        for item in data["source_breakdown"]:
            source = item["_id"] or "Unknown"
            source_breakdown[source] = item["count"]

        # Format industry breakdown
        industry_breakdown = {}
        for item in data["industry_breakdown"]:
            industry = item["_id"] or "Unknown"
            industry_breakdown[industry] = item["count"]

        # Format interest by platform
        interest_by_platform = {}
        for item in data["interest_by_platform"]:
            platform = item["_id"]["platform"] or "Unknown"
            interest = item["_id"]["interest"] or "Low"

            if platform not in interest_by_platform:
                interest_by_platform[platform] = {}

            interest_by_platform[platform][interest] = item["count"]

        return {
            **status_counts,
            "lead_sources_breakdown": source_breakdown,
            "leads_by_industry": industry_breakdown,
            "interest_by_platform": interest_by_platform
        }

    @staticmethod
    async def get_recent_leads(
        db: AsyncIOMotorDatabase,
        limit: int,
        skip: int,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent leads with filters and pagination"""
        match_filter = {}

        if status:
            match_filter["status"] = status

        if platform:
            match_filter["lead_source"] = platform

        if user_id:
            match_filter["user_id"] = user_id

        pipeline = [
            {"$match": match_filter} if match_filter else {"$match": {}},
            {"$sort": {"date_created": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": AdminLeadAnalyticsRepository.USERS_COLLECTION,
                    "let": {"userId": {"$toObjectId": "$user_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$userId"]}}},
                        {"$project": {"email": 1, "firstName": 1, "lastName": 1}}
                    ],
                    "as": "user_info"
                }
            },
            {
                "$unwind": {
                    "path": "$user_info",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$project": {
                    "lead_id": {"$toString": "$_id"},
                    "name": "$lead_full_name",
                    "email": "$lead_email",
                    "platform": "$lead_source",
                    "status": 1,
                    "interest_level": 1,
                    "intent_score": 1,
                    "relevance_score": 1,
                    "created_date": "$date_created",
                    "assigned_to": "$assigned_to",
                    "user_email": "$user_info.email",
                    "user_name": {
                        "$concat": [
                            {"$ifNull": ["$user_info.firstName", ""]},
                            " ",
                            {"$ifNull": ["$user_info.lastName", ""]}
                        ]
                    }
                }
            }
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)
        return result

    @staticmethod
    async def count_leads_with_filters(
        db: AsyncIOMotorDatabase,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> int:
        """Count leads with filters"""
        match_filter = {}

        if status:
            match_filter["status"] = status

        if platform:
            match_filter["lead_source"] = platform

        if user_id:
            match_filter["user_id"] = user_id

        count = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].count_documents(match_filter)
        return count

    @staticmethod
    async def get_top_users_with_metrics(
        db: AsyncIOMotorDatabase,
        start_date: datetime,
        end_date: datetime,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get top users with detailed metrics"""
        pipeline = [
            {
                "$match": {
                    "date_created": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "total_leads": {"$sum": 1},
                    "qualified_leads": {
                        "$sum": {"$cond": [{"$eq": ["$status", "qualified"]}, 1, 0]}
                    },
                    "converted_leads": {
                        "$sum": {"$cond": [{"$eq": ["$status", "converted"]}, 1, 0]}
                    }
                }
            },
            {
                "$addFields": {
                    "conversion_rate": {
                        "$cond": [
                            {"$gt": ["$qualified_leads", 0]},
                            {
                                "$multiply": [
                                    {"$divide": ["$converted_leads", "$qualified_leads"]},
                                    100
                                ]
                            },
                            0
                        ]
                    }
                }
            },
            {"$sort": {"total_leads": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": AdminLeadAnalyticsRepository.USERS_COLLECTION,
                    "let": {"userId": {"$toObjectId": "$_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$userId"]}}},
                        {"$project": {"email": 1, "firstName": 1, "lastName": 1}}
                    ],
                    "as": "user_info"
                }
            },
            {
                "$unwind": {
                    "path": "$user_info",
                    "preserveNullAndEmptyArrays": True
                }
            }
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)

        formatted_result = []
        for item in result:
            user_info = item.get("user_info", {})
            formatted_result.append({
                "user_id": item["_id"],
                "email": user_info.get("email", "Unknown"),
                "name": f"{user_info.get('firstName', '')} {user_info.get('lastName', '')}".strip() or "Unknown",
                "total_leads": item["total_leads"],
                "qualified_leads": item["qualified_leads"],
                "converted_leads": item["converted_leads"],
                "conversion_rate": round(item["conversion_rate"], 2)
            })

        return formatted_result

    @staticmethod
    async def get_daily_lead_trends(
        db: AsyncIOMotorDatabase,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get daily lead generation trends"""
        pipeline = [
            {
                "$match": {
                    "date_created": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$date_created"
                        }
                    },
                    "total": {"$sum": 1},
                    "new": {
                        "$sum": {"$cond": [{"$eq": ["$status", "new"]}, 1, 0]}
                    },
                    "contacted": {
                        "$sum": {"$cond": [{"$eq": ["$status", "contacted"]}, 1, 0]}
                    },
                    "qualified": {
                        "$sum": {"$cond": [{"$eq": ["$status", "qualified"]}, 1, 0]}
                    },
                    "converted": {
                        "$sum": {"$cond": [{"$eq": ["$status", "converted"]}, 1, 0]}
                    }
                }
            },
            {"$sort": {"_id": 1}}
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)

        formatted_result = []
        for item in result:
            formatted_result.append({
                "date": item["_id"],
                "total": item["total"],
                "new": item["new"],
                "contacted": item["contacted"],
                "qualified": item["qualified"],
                "converted": item["converted"]
            })

        return formatted_result

    @staticmethod
    async def get_conversion_funnel_data(
        db: AsyncIOMotorDatabase,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get conversion funnel with stage progression"""
        match_filter = {
            "date_created": {"$gte": start_date, "$lte": end_date}
        }

        if user_id:
            match_filter["user_id"] = user_id

        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": None,
                    "new": {"$sum": {"$cond": [{"$eq": ["$status", "new"]}, 1, 0]}},
                    "contacted": {"$sum": {"$cond": [{"$eq": ["$status", "contacted"]}, 1, 0]}},
                    "qualified": {"$sum": {"$cond": [{"$eq": ["$status", "qualified"]}, 1, 0]}},
                    "converted": {"$sum": {"$cond": [{"$eq": ["$status", "converted"]}, 1, 0]}},
                    "total": {"$sum": 1}
                }
            }
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)

        if not result:
            return {
                "stages": [],
                "total_leads": 0
            }

        data = result[0]
        total = data["total"]

        stages = [
            {
                "stage": "New",
                "count": data["new"],
                "percentage": round((data["new"] / total * 100) if total > 0 else 0, 2)
            },
            {
                "stage": "Contacted",
                "count": data["contacted"],
                "percentage": round((data["contacted"] / total * 100) if total > 0 else 0, 2),
                "conversion_from_previous": round((data["contacted"] / data["new"] * 100) if data["new"] > 0 else 0, 2)
            },
            {
                "stage": "Qualified",
                "count": data["qualified"],
                "percentage": round((data["qualified"] / total * 100) if total > 0 else 0, 2),
                "conversion_from_previous": round((data["qualified"] / data["contacted"] * 100) if data["contacted"] > 0 else 0, 2)
            },
            {
                "stage": "Converted",
                "count": data["converted"],
                "percentage": round((data["converted"] / total * 100) if total > 0 else 0, 2),
                "conversion_from_previous": round((data["converted"] / data["qualified"] * 100) if data["qualified"] > 0 else 0, 2)
            }
        ]

        return {
            "stages": stages,
            "total_leads": total
        }

    @staticmethod
    async def get_platform_metrics(
        db: AsyncIOMotorDatabase,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get performance metrics by platform"""
        pipeline = [
            {
                "$match": {
                    "date_created": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$lead_source",
                    "total_leads": {"$sum": 1},
                    "avg_intent_score": {"$avg": "$intent_score"},
                    "avg_relevance_score": {"$avg": "$relevance_score"},
                    "converted": {
                        "$sum": {"$cond": [{"$eq": ["$status", "converted"]}, 1, 0]}
                    },
                    "qualified": {
                        "$sum": {"$cond": [{"$eq": ["$status", "qualified"]}, 1, 0]}
                    }
                }
            },
            {
                "$addFields": {
                    "conversion_rate": {
                        "$cond": [
                            {"$gt": ["$qualified", 0]},
                            {
                                "$multiply": [
                                    {"$divide": ["$converted", "$qualified"]},
                                    100
                                ]
                            },
                            0
                        ]
                    }
                }
            },
            {"$sort": {"total_leads": -1}}
        ]

        result = await db[AdminLeadAnalyticsRepository.LEADS_COLLECTION].aggregate(pipeline).to_list(None)

        formatted_result = []
        for item in result:
            formatted_result.append({
                "platform": item["_id"] or "Unknown",
                "total_leads": item["total_leads"],
                "avg_intent_score": round(item.get("avg_intent_score") or 0, 2),
                "avg_relevance_score": round(item.get("avg_relevance_score") or 0, 2),
                "conversion_rate": round(item["conversion_rate"], 2)
            })

        return formatted_result
