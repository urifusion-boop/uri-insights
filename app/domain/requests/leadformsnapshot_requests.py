from typing import Optional, List
from pydantic import BaseModel, Field
from app.domain.enums.apollo_enum import ContactEmailStatusEnum, PersonSenioritiesEnum
from app.domain.enums.leadform_enum import LeadFormTypeEnum


class LeadFormSnapshotFilterQuery(BaseModel):
    user_id: Optional[str] = Field(
        None, description="User ID associated with the snapshot"
    )
    lead_form_id: Optional[str] = Field(
        None, description="Lead form ID that this snapshot belongs to"
    )
    form_type: Optional[LeadFormTypeEnum] = Field(
        None,
        description="Type of lead form (PERSON, ORGANIZATION, CONVERSATIONAL, BUSINESS)",
    )
    form_title: Optional[str] = Field(
        None, description="Title of the form (optional filter)"
    )

    # Person search filters
    q_keywords: Optional[str] = Field(None)

    # Organization filters
    revenue_range_min: Optional[int] = Field(None)
    revenue_range_max: Optional[int] = Field(None)
    q_organization_name: Optional[str] = Field(None)

    # Business filters
    business_name: Optional[str] = Field(None)
    business_summary: Optional[str] = Field(None)
    business_website: Optional[str] = Field(None)

    class Config:
        use_enum_values = True
