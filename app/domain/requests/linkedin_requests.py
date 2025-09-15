from typing import Any, Dict

from fastapi import Query
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.linkedin_enum import (
    LinkedInPostRetrievalOrderEnum,
    LinkedInTimeGranularityEnum,
    LinkedInVisibilityEnum,
)
from app.domain.models.linkedin_model import *


class LinkedInRequestModel(LinkedInModel):
    bearer_token: str


class CreateCampaignGroupRequest(LinkedInRequestModel):
    account: str
    name: str
    runSchedule: LinkedinScheduleModel
    status: str
    totalBudget: LinkedinAmountModel


class UpdateCampaignGroupRequest(LinkedInRequestModel):
    ad_account_id: str
    campaign_group_id: str
    set: Dict[str, Dict[str, Any]]


class CreateCampaignRequest(LinkedInRequestModel):
    ad_account_id: str
    campaign_group_id: str
    daily_budget: LinkedinAmountModel
    audience_expansion_enabled: bool
    cost_type: str
    # connected_television_only: bool
    creative_selection: str
    locale: LinkedinLocaleModel
    name: str
    offsite_delivery_enabled: bool
    # optimization_preference: LinkedinOptimizationPreferenceModel
    run_schedule: LinkedinScheduleModel
    targeting_criteria: LinkedinTargetingCriteriaModel
    type: str
    unit_cost: LinkedinAmountModel
    status: str


class UpdateCampaignRequest(LinkedInRequestModel):
    ad_account_id: str
    campaign_id: str
    set: Dict[str, Dict[str, Any]]


class CreateConversionRuleRequest(LinkedInRequestModel):
    name: str
    account_id: str
    conversion_method: str
    post_click_attribution_window_size: int
    view_through_attribution_window_size: int
    attribution_type: str
    type: str


class StreamConversionEventRequest(LinkedInRequestModel):
    conversion_id: str
    conversion_happened_at: str
    conversion_value: LinkedinAmountModel
    user: LinkedinUserModel
    event_id: str


class LinkConversionToCampaignRequest(LinkedInRequestModel):
    campaign_id: str
    conversion_id: str


class ShareAnnotation(BaseModel):
    entity: str
    length: int
    start: int


class ShareText(BaseModel):
    annotations: List[ShareAnnotation]
    text: str


class ShareContentEntity(BaseModel):
    entityLocation: str
    thumbnails: List[Dict[str, str]]


class ShareContent(BaseModel):
    contentEntities: List[ShareContentEntity]
    title: str


class ShareDistribution(BaseModel):
    linkedInDistributionTarget: Dict[str, Any] = {}


class SharePayload(BaseModel):
    owner: str
    text: ShareText
    subject: str
    distribution: ShareDistribution
    content: ShareContent


class SubscriptionPayload(BaseModel):
    webhook: str


class ShareCommentary(BaseModel):
    text: str


class ComLinkedinUgcShareTextContent(BaseModel):
    shareCommentary: ShareCommentary
    shareMediaCategory: str = "NONE"


class Description(BaseModel):
    text: str


class Title(BaseModel):
    text: str


class ArticleItem(BaseModel):
    status: str
    description: Description
    originalUrl: str
    title: Title


class MediaItem(BaseModel):
    status: str
    description: Description
    media: str
    title: Title


class ComLinkedinUgcShareArticleContent(ComLinkedinUgcShareTextContent):
    media: List[ArticleItem]


class ComLinkedinUgcShareMediaContent(ComLinkedinUgcShareTextContent):
    media: List[MediaItem]


class SpecificTextContent(BaseModel):
    com_linkedin_ugc_ShareContent: ComLinkedinUgcShareTextContent = Field(
        ..., alias="com.linkedin.ugc.ShareContent"
    )

    class Config:
        populate_by_name = True  # Allows population using field names or aliases


class SpecificArticleContent(BaseModel):
    com_linkedin_ugc_ShareContent: ComLinkedinUgcShareArticleContent = Field(
        ..., alias="com.linkedin.ugc.ShareContent"
    )

    class Config:
        populate_by_name = True


class SpecificMediaContent(BaseModel):
    com_linkedin_ugc_ShareContent: ComLinkedinUgcShareMediaContent = Field(
        ..., alias="com.linkedin.ugc.ShareContent"
    )

    class Config:
        populate_by_name = True


class Visibility(BaseModel):
    com_linkedin_ugc_MemberNetworkVisibility: str = Field(
        ..., alias="com.linkedin.ugc.MemberNetworkVisibility"
    )

    class Config:
        populate_by_name = True  # Allows population using field names or aliases
        alias_generator = None  # Prevents any automatic aliasing


class BaseShareContentPayload(BaseModel):
    author: str
    lifecycleState: str = "PUBLISHED"
    visibility: Visibility


class ShareTextContentPayload(BaseShareContentPayload):
    specificContent: SpecificTextContent


class ShareArticleContentPayload(BaseShareContentPayload):
    specificContent: SpecificArticleContent


class ShareMediaContentPayload(BaseShareContentPayload):
    specificContent: SpecificMediaContent


class ServiceRelationship(BaseModel):
    relationship_type: str = Field(..., alias="relationshipType")
    identifier: str

    class Config:
        populate_by_name = True


class RegisterUploadRequest(BaseModel):
    recipes: List[str]
    owner: str
    service_relationships: List[ServiceRelationship] = Field(
        ..., alias="serviceRelationships"
    )

    class Config:
        populate_by_name = True


class GetUploadUrlPayload(BaseModel):
    register_upload_request: RegisterUploadRequest = Field(
        ..., alias="registerUploadRequest"
    )

    class Config:
        populate_by_name = True


class GetSharePayload(BaseModel):
    id: str


class LinkedinSocialMediaPostSettings(BaseModel):
    visibility: LinkedInVisibilityEnum
    description: str
    title: str

    class Config:
        use_enum_values = True


class TimeBoundStatistics(BaseModel):
    organization_id: str
    date_range: DateFilterEnum = DateFilterEnum.LAST_1_WEEK
    time_granularity: LinkedInTimeGranularityEnum = LinkedInTimeGranularityEnum.DAY

    class Config:
        use_enum_values = True
