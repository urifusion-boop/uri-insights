from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.helpers.dict_helper import DictHelper
from app.core.helpers.lead_helper import LeadHelper
from app.core.helpers.text_helper import TextHelper
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.exporttype_enum import ExportTypeEnum
from app.domain.enums.filetype_enum import FileTypeEnum
from app.domain.requests.export_requests import FileExportRequest
from app.domain.requests.lead_requests import GetLeadsByFiltersRequest
from app.repository.LeadFormSnapshotRepository import LeadFormSnapshotRepository
from app.repository.LeadRepository import LeadRepository


class LeadExporter:
    @staticmethod
    async def _fetch_leads(
        db: AsyncIOMotorDatabase,
        filters: GetLeadsByFiltersRequest,
        skip: int,
        limit: int,
        date_filter: Optional[DateFilterEnum] = None,
    ) -> List[dict]:
        response = await LeadRepository.get_leads_by_filters(
            db=db, filters=filters, skip=skip, limit=limit, date_filter=date_filter
        )
        return response.get("responseData", {}).get("data", [])

    @staticmethod
    async def _resolve_form_title(
        db: AsyncIOMotorDatabase, filters: GetLeadsByFiltersRequest
    ) -> str:
        if filters.lead_form_snapshot_id:
            snapshot = await LeadFormSnapshotRepository.get_by_id(
                db, filters.lead_form_snapshot_id
            )
            return snapshot.get("responseData", {}).get("form_title", "")
        elif filters.lead_type:
            return LeadHelper.get_lead_type_for_notification(filters.lead_type.value)
        else:
            return ""

    @staticmethod
    def _format_leads_for_export(leads: List[dict]) -> None:
        from datetime import datetime

        for lead in leads:
            lead_type = lead.get("lead_type", "")

            # Common fields for all lead types
            common_keys = [
                "username",
                "first_name",
                "last_name",
                "location",
                "tags",
                "lead_status",
                "interest_level",
                "lead_source",
                "lead_type",
                "created_date",
                "last_updated",
                "starred",
            ]

            if lead_type == "CONVERSATIONAL":
                # Fields shown in conversational leads table
                keys_to_include = [
                    "username",
                    "first_name",
                    "last_name",
                    "picture_url",
                    "lead_reason",
                    "lead_status",
                    "tags",
                    "opportunity_type",
                    "lead_link",
                    "linkedin_url",
                    "facebook_url",
                    "twitter_url",
                    "github_url",
                    "website_url",
                    "created_date",
                ]
            else:
                # Fields shown in individual/person/organization/business leads table
                keys_to_include = [
                    "username",
                    "first_name",
                    "last_name",
                    "job_title",
                    "picture_url",
                    "company_name",
                    "industry",
                    "company_logo",
                    "lead_email",
                    "phone",
                    "location",
                    "tags",
                    "lead_status",
                    "linkedin_url",
                    "facebook_url",
                    "twitter_url",
                    "github_url",
                    "website_url",
                    "created_date",
                ]

            DictHelper.include_keys(lead, keys_to_include)

            # Convert datetime objects to ISO string format
            if "created_date" in lead and isinstance(lead["created_date"], datetime):
                lead["created_date"] = lead["created_date"].isoformat()
            if "last_updated" in lead and isinstance(lead["last_updated"], datetime):
                lead["last_updated"] = lead["last_updated"].isoformat()

    @staticmethod
    def _build_export_request(
        user_id: Optional[str],
        file_type: FileTypeEnum,
        form_title: str,
        data: List[dict],
    ) -> FileExportRequest:
        if not user_id:
            raise ValueError("USer ID not provided in build export request.")
        return FileExportRequest(
            userId=user_id,
            fileType=file_type.value,
            exportType=ExportTypeEnum.LEAD_DATA.value,
            exportName=TextHelper.generate_export_name(
                form_title, ExportTypeEnum.LEAD_DATA.value
            ),
            data=data,
        )
