from typing import Any, Dict, Optional
from agents import RunContextWrapper, function_tool

from app.database import get_db
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.requests.lead_requests import GetLeadsByFiltersRequest
from app.repository.LeadRepository import LeadRepository


@function_tool()
async def get_leads_by_filters_tool(
    ctx: RunContextWrapper[dict[str, Any]],
    filters: GetLeadsByFiltersRequest,
    skip: int = 0,
    limit: int = 10,
    date_filter: Optional[DateFilterEnum] = None,
) -> Dict[str, Any]:
    """
    Retrieve leads using filter criteria and optional date filtering.
    """
    print("Tool function get_leads_by_filters_tool called.")
    print("With context: ", ctx.context)
    user_id = ctx.context.get("user_id", "")

    filters.assigned_to = user_id
    print("Filters: ", filters)

    result = await LeadRepository.get_leads_by_filters(
        db=get_db(),
        filters=filters,
        date_filter=date_filter,
        skip=skip,
        limit=limit,
    )

    return result
