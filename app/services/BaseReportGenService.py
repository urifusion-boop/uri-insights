from datetime import datetime
import inspect
from abc import ABC, abstractmethod
import json
import traceback
from typing import Any, Dict, List, Set, Tuple, Optional

from pydantic import BaseModel

from app.core.helpers.date_helper import DateHelper
from app.core.helpers.reportgeneration_helper import ReportGenerationHelper
from app.domain.enums.microservicestype_enum import MicroServiceTypeEnum
from app.domain.enums.queue_message_type_enum import (
    AuditLogQueueMessageTypeEnum,
    FileGenerationQueueMessageTypeEnum,
)
from app.domain.enums.reportgeneration_enum import (
    ReportGenSectionKeyEnum,
    ReportGenSectionMethodsEnum,
    ReportGenerationTypeEnum,
)
from app.domain.requests.reportgeneration_requests import (
    MultiAccReportGenericType,
    ReportGenerationRequest,
)
from app.domain.responses.reportgeneration_response import (
    AccountInfo,
    KPIAnalysis,
    Overview,
    PerformanceMetrics,
    ReportModel,
)
from app.domain.responses.uri_response import UriResponse
from app.services.NotificationService import NotificationService
from app.services.ReportGenAiService import ReportGenAiService
from app.services.azure.producers.AuditLogProducer import AuditLogQueueProducerService
from app.services.azure.producers.ExceptionLogProducer import (
    ExceptionLogQueueProducerService,
)


class BaseReportGenerator(ABC):
    """
    Abstract base class for all report generators.
    Defines the template for section execution and orchestration.
    """

    ACCOUNT_TRACKING_GENERIC_EXCEPTION_MESSAGE = (
        "An error occurred in generating your account tracking report"
    )
    HASHTAG_TRACKING_GENERIC_EXCEPTION_MESSAGE = (
        "An error occurred in generating you hashtag tracking report"
    )

    # Core sections (key, method_name)
    SECTION_ORDER: List[Tuple[str, str]] = [
        (
            ReportGenSectionKeyEnum.ACCOUNT_INFO.value,
            ReportGenSectionMethodsEnum.ACCOUNT_INFO.value,
        ),
        (
            ReportGenSectionKeyEnum.OVERVIEW.value,
            ReportGenSectionMethodsEnum.OVERVIEW.value,
        ),
        (
            ReportGenSectionKeyEnum.HIGHLIGHTS.value,
            ReportGenSectionMethodsEnum.HIGHLIGHTS.value,
        ),
        (
            ReportGenSectionKeyEnum.PERFORMANCE_METRICS.value,
            ReportGenSectionMethodsEnum.PERFORMANCE_METRICS.value,
        ),
        (
            ReportGenSectionKeyEnum.KPI_ANALYSIS.value,
            ReportGenSectionMethodsEnum.KPI_ANALYSIS.value,
        ),
        (
            ReportGenSectionKeyEnum.KEY_METRICS.value,
            ReportGenSectionMethodsEnum.KEY_METRICS.value,
        ),
        (
            ReportGenSectionKeyEnum.RECOMMENDATIONS.value,
            ReportGenSectionMethodsEnum.RECOMMENDATIONS.value,
        ),
    ]

    # Sections that must always run regardless of user input
    MANDATORY: set = {
        ReportGenSectionKeyEnum.ACCOUNT_INFO.value,
        ReportGenSectionKeyEnum.OVERVIEW.value,
        ReportGenSectionKeyEnum.HIGHLIGHTS.value,
        ReportGenSectionKeyEnum.PERFORMANCE_METRICS.value,
        ReportGenSectionKeyEnum.KPI_ANALYSIS.value,
        ReportGenSectionKeyEnum.KEY_METRICS.value,
    }

    def __init__(self, db: Any, request: ReportGenerationRequest, cache_key: str):
        self.db = db
        self.request: ReportGenerationRequest = request
        self.cache_key: str = cache_key
        self.metadata: Optional[Dict[str, Any]] = None
        self.account_info: Optional[AccountInfo] = None
        self.performance_metrics: Optional[
            PerformanceMetrics
            | MultiAccReportGenericType[
                PerformanceMetrics, PerformanceMetrics, PerformanceMetrics
            ]
        ] = None
        self.report_data: Optional[dict] = None

    @classmethod
    def section_order(cls) -> List[Tuple[str, str]]:
        """
        Return the ordered list of sections to execute,
        including any EXTRA_SECTIONS defined in subclasses.
        """
        extra = getattr(cls, "EXTRA_SECTIONS", [])
        return cls.SECTION_ORDER + extra

    @classmethod
    def mandatory_section_order(cls) -> set:
        extra: Set = getattr(cls, "EXTRA_MANDATORY_SECTIONS", set())
        return cls.MANDATORY | extra

    async def generate(self) -> Optional[ReportModel]:
        """
        Orchestrate execution of requested and mandatory sections,
        collect results, and return a populated ReportModel.
        """
        url = self._build_report_url()

        try:
            await self._fetch_metadata()
            final_report = await self._execute_sections()

            await self._handle_success(final_report, url)
            return final_report

        except Exception as e:
            await self._handle_failure(e, url)
        finally:
            return None

    async def _execute_sections(self) -> ReportModel:
        wanted = {field.value for field in self.request.included_fields}
        mandatory = self.mandatory_section_order()
        # 1. Execute and collect
        output: Dict[str, Any] = {}
        for key, method_name in self.section_order():
            if key not in mandatory and key not in wanted:
                continue

            method = getattr(self, method_name)
            result = method()
            if result:
                key = ReportGenerationHelper.section_name_to_attribute_map.get(key, key)
                if inspect.iscoroutine(result):
                    result = await result
                output[key] = result
                self.report_data = output

        # 2. Build and return final Pydantic model
        return ReportModel(**output)

    def _build_report_url(self) -> str:
        if self.request.report_generation_type:
            report_type = self.request.report_generation_type.value.lower().replace(
                "_", "-"
            )
            return f"/report/{report_type}/generate"
        else:
            raise ValueError(
                "request.report_generation_type is empty therefore report gen result handling failed."
            )

    async def _handle_success(self, report: ReportModel, url: str) -> None:
        report_dict = report.dict(exclude_none=True)
        await NotificationService.notify_report_generation(report_dict)

        audit_log = {
            "userId": self.request.user_id,
            "action": f"Request POST {url}",
            "method": "POST",
            "url": url,
            "status": "SUCCESS",
            "serviceType": MicroServiceTypeEnum.URI_INSIGHTS.value,
        }
        await AuditLogQueueProducerService.publish_audit_log(
            audit_log, AuditLogQueueMessageTypeEnum.USER_ACTIVITY
        )

    async def _handle_failure(self, e: Exception, url: str) -> None:
        exception_log = {
            "userId": self.request.user_id,
            "exceptionDate": datetime.utcnow().isoformat(),
            "method": "POST",
            "url": url,
            "status": 500,
            "exception": "".join(
                traceback.format_exception(type(e), e, e.__traceback__)
            ),
            "serviceType": MicroServiceTypeEnum.URI_INSIGHTS.value,
        }

        email_msg = self._map_exception_to_email(str(e))

        report_error_data = {
            "email": self.request.recipient,
            "message": email_msg,
        }

        await ExceptionLogQueueProducerService.publish_exception_log(exception_log)
        await NotificationService.notify_report_generation(
            report_error_data,
            FileGenerationQueueMessageTypeEnum.PERFORMANCE_REPORT_ERROR,
        )

    def _map_exception_to_email(self, msg: str) -> str:
        if msg == "An error occurred in generating your":
            return msg
        elif "has not been tracked," in msg:
            return msg
        else:
            return (
                "There was an unexpected error generating your report. "
                "Please reach out to customer service."
            )

    # Abstract methods for subclasses to implement each core section
    @abstractmethod
    async def _fetch_metadata(self) -> None:
        """
        Load any report-type-specific raw data into self.metadata,
        so that all get_* methods can use it.
        """
        pass

    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        report_gen_request = self.request
        report_gen_subtypes = self.request.report_generation_subtypes
        start_date, end_date = DateHelper.get_date_range(report_gen_request.period)

        date_range_str = (
            f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}"
        )
        if self.metadata:
            account_info = self.metadata.get("account_info", {})
            if (
                self.request.report_generation_type
                == ReportGenerationTypeEnum.ACCOUNT_TRACKING
            ):
                account_name = await ReportGenAiService.get_account_name(self.metadata)
                social_username = await ReportGenAiService.get_account_name(
                    self.metadata
                )
            else:
                account_name = account_info.get("name")
                social_username = account_info.get("username") or account_info.get(
                    "name"
                )
            account_overview_data = {
                "userId": report_gen_request.user_id,
                "accountName": account_name,
                "reportType": report_gen_request.report_generation_type,
                "hashtag": account_info.get("hashtag"),
                "platforms": report_gen_subtypes,
                "period": date_range_str,
                "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "socialUsername": social_username,
                "recipient": report_gen_request.recipient,
            }

            # Remove keys with None values
            filtered_data = {
                k: v for k, v in account_overview_data.items() if v is not None
            }
            result = AccountInfo(**filtered_data)

            self.account_info = result

            return result
        else:
            raise ValueError("Metadata is missing for report generation")

    @abstractmethod
    async def get_overview(self) -> Overview:
        if not self.request.included_fields:
            raise ValueError("No included fields selected by user")

        fields = [item.value for item in self.request.included_fields]
        report_focus = ", ".join(fields)

        if self.account_info and self.request.report_generation_type:
            ai_report_overview = await ReportGenAiService.generate_ai_report_overview(
                self.account_info.dict(exclude_none=True),
                report_focus,
                self.request.report_generation_type,
            )
        if not ai_report_overview:
            raise ValueError("AI report overview not generated successfully")

        return Overview(**ai_report_overview)

    @abstractmethod
    async def get_highlights(self) -> Any:
        if self.metadata:
            current_period_insights = self.metadata.get("current_period_insights", {})
            previous_period_insights = self.metadata.get("previous_period_insights", {})

            if self.request.report_generation_type:
                ai_report_highlights = (
                    await ReportGenAiService.generate_report_highlights(
                        current_period_insights=current_period_insights,
                        previous_period_insights=previous_period_insights,
                        report_type=self.request.report_generation_type,
                    )
                )
            if not ai_report_highlights:
                raise ValueError("AI report highlights not generated successfully")
            result = ai_report_highlights.get("highlights")
            return result

    @abstractmethod
    async def get_performance_metrics(self) -> Any:
        if self.account_info and self.request.report_generation_type:
            account_info = (
                self.account_info.model_dump(exclude_none=True)
                if isinstance(self.account_info, BaseModel)
                else self.account_info
            )
            performance_section_text = (
                await ReportGenAiService.generate_report_performance_section_text(
                    account_info,
                    self.request.report_generation_type,
                )
            )
            return performance_section_text
        if not performance_section_text:
            print("Failed to generate performance section text")
            return None

    @abstractmethod
    async def get_kpi_analysis(self) -> KPIAnalysis:
        if (
            not self.metadata
            or not self.performance_metrics
            or not self.request.report_generation_type
        ):
            raise ValueError(
                "Metadata, performance metrics or report type is missing for KPI analysis of report generation"
            )
        post_data = self.metadata.get("post_data", [])
        ai_kpi_analysis = await ReportGenAiService.generate_kpi_analysis(
            self.performance_metrics.dict(exclude_none=True),
            post_data,
            self.request.report_generation_type,
        )

        if not ai_kpi_analysis:
            raise ValueError("KPI analysis not generated successfully")

        return KPIAnalysis(**ai_kpi_analysis)

    @abstractmethod
    async def get_key_metrics(self) -> Any:
        pass

    @abstractmethod
    async def get_ai_recommendations(self) -> Any:
        if self.report_data and self.request.report_generation_type:
            recommendations_data = await ReportGenAiService.generate_ai_recommendations(
                self.report_data, self.request.report_generation_type
            )
            return recommendations_data

    @abstractmethod
    async def calculate_performance_metrics(self) -> Any:
        pass
