from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, model_validator

from app.core.helpers.list_helper import ListHelper
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.enums.reportgeneration_enum import (
    ReportGenSectionKeyEnum,
    ReportGenerationTypeEnum,
)
from pydantic.generics import GenericModel

# Define generic type variables
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")


class MultiAccReportGenericType(GenericModel, Generic[T1, T2, T3]):
    instagram: Optional[T1] = None
    facebook: Optional[T2] = None
    linkedin: Optional[T3] = None


class ReportGenerationRequest(BaseModel):
    influencer_ids: Optional[MultiAccReportGenericType[str, str, str]] = Field(
        None, description="IDs of the influencer(s)"
    )
    user_id: str = Field(
        ..., description="ID of the user initiating the report generation"
    )
    tracker_id: Optional[str] = Field(
        None, description="ID of the keyword tracker, if applicable"
    )
    recipient: Optional[str] = Field(None, description="Recipient's email")
    period: DateFilterEnum = Field(..., description="Time window for the report")
    report_generation_type: Optional[ReportGenerationTypeEnum] = Field(
        None, description="Report category"
    )
    report_generation_subtypes: Optional[List[PostPlatformEnum]] = Field(
        None, description="Sub-type (e.g. platform) for the report"
    )
    included_fields: List[ReportGenSectionKeyEnum] = Field(
        None,
        description="""
        List of section keys the user wants in the report (e.g. ['overview','recentHashtags']).
        """,
    )

    @model_validator(mode="before")
    @classmethod
    def check_type_specific_requirements(cls, values):
        rtype = values.get("report_generation_type")
        rsubtype = values.get("report_generation_subtypes")
        if rtype == ReportGenerationTypeEnum.ACCOUNT_TRACKING.value:
            if not values.get("influencer_ids"):
                raise ValueError(
                    "influencer_ids field is required for account-tracking reports"
                )
            if not rsubtype:
                raise ValueError(
                    "report_generation_subtypes field is required for account-tracking reports"
                )
            if ListHelper.has_duplicates(rsubtype):
                raise ValueError(
                    "You cannot generate a report with multiple accounts from the same social media platform."
                )
        elif (
            rtype == ReportGenerationTypeEnum.KEYWORD_TRACKING.value
            or rtype == ReportGenerationTypeEnum.HASHTAG_TRACKING.value
        ):
            if rsubtype:
                values["report_generation_subtypes"] = None
            if not values.get("tracker_id"):
                raise ValueError(
                    "tracker_id is required for hashtag tracking and keyword tracking reports"
                )

        return values
