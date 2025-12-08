from typing import Type
from fastapi import BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums.reportgeneration_enum import ReportGenerationTypeEnum
from app.domain.requests.reportgeneration_requests import ReportGenerationRequest
from app.domain.responses.uri_response import UriResponse

from app.services.AccountTrackingReportGenService import (
    AccountTrackingReportGenService,
)
from app.services.HashtagTrackingReportGen import (
    HashtagTrackingReportGenService,
)


class ReportGenerationService:
    _report_generator_map: dict[ReportGenerationTypeEnum, Type] = {
        ReportGenerationTypeEnum.ACCOUNT_TRACKING: AccountTrackingReportGenService,
        ReportGenerationTypeEnum.HASHTAG_TRACKING: HashtagTrackingReportGenService,
    }

    @classmethod
    def _get_report_generator_class(cls, report_type: ReportGenerationTypeEnum) -> Type:
        if report_type not in cls._report_generator_map:
            raise ValueError(f"Unsupported Report Type: {report_type.value}")
        return cls._report_generator_map[report_type]

    @staticmethod
    async def generate_user_report(
        db: AsyncIOMotorDatabase,
        report_generation_type: ReportGenerationTypeEnum,
        report_generation_data: ReportGenerationRequest,
        background_tasks: BackgroundTasks,
    ):
        generator_class = ReportGenerationService._get_report_generator_class(
            report_generation_type
        )

        report_generation_data.report_generation_type = report_generation_type

        # Instantiate the report generator (standardized constructor)
        generator = await generator_class.async_init(
            request=report_generation_data, db=db
        )

        # Dynamically call a unified method in the background
        background_tasks.add_task(generator.generate)

        # Track trial usage for report generation (non-blocking)
        try:
            from app.services.uri_microservices.UriBackendService import UriBackendService
            await UriBackendService.increment_trial_usage(
                user_id=report_generation_data.user_id,
                field="trialReportsGenerated",
                amount=1
            )
        except Exception as e:
            print(f"Failed to track trial usage for report generation: {e}")

        return UriResponse.custom_response(
            f"""Your {
                report_generation_type.value.lower().replace('_', ' ')
            } report is being generated, you will receive an email within 5 minutes.""",
            202,
            True,
        )
