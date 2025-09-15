from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict
from bson import ObjectId
from app.domain.aliases import to_camel


class LinkedInModel(BaseModel):
    class Config:
        alias_generator = to_camel
        populate_by_name = True


class LinkedinUserInfoModel(LinkedInModel):
    first_name: str
    last_name: str
    title: str
    company_name: str
    country_code: str


class LinkedinAmountModel(LinkedInModel):
    amount: str
    currency_code: str


class LinkedinLocaleModel(LinkedInModel):
    country: str
    language: str


class LinkedinScheduleModel(LinkedInModel):
    start: int
    end: int


class LinkedinTimeSpanModel(LinkedInModel):
    duration: int
    unit: str


class LinkedinFrequencyOptimizationPreferenceModel(LinkedInModel):
    time_span: LinkedinTimeSpanModel
    optimization_type: str
    frequency: int


class LinkedinOptimizationPreferenceModel(LinkedInModel):
    frequency_optimization_preference: LinkedinFrequencyOptimizationPreferenceModel


class LinkedinTargetingCriteriaModel(LinkedInModel):
    include: Dict[str, List[Dict[str, Dict[str, List[str]]]]]


class LinkedinUserIdModel(LinkedInModel):
    id_type: str
    id_value: str


class LinkedinUserModel(LinkedInModel):
    user_ids: List[LinkedinUserIdModel]
    user_info: LinkedinUserInfoModel
