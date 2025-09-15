from pydantic import BaseModel
from typing import List, Optional, Union

from app.domain.requests.reportgeneration_requests import MultiAccReportGenericType


class AccountInfo(BaseModel):
    userId: str
    accountName: Optional[str] = None
    reportType: str
    period: str
    date: str
    hashtag: Optional[str] = None
    platforms: Optional[List[str]] = None
    socialUsername: Optional[str] = None
    recipient: Optional[str] = None


class Overview(BaseModel):
    summary: str


class KPI(BaseModel):
    kpi: str
    currentPeriod: Union[str, int, float]
    previousPeriod: Union[str, int, float]
    change: str


class PerformanceMetrics(BaseModel):
    text: str
    kpis: List[KPI] | MultiAccReportGenericType[List[KPI], List[KPI], List[KPI]]


class KPIAnalysis(BaseModel):
    working: List[str]
    improvements: List[str]


class KeyMetrics(BaseModel):
    totalFollowers: Optional[int] = None
    totalViewers: Optional[int] = None
    totalPosts: Optional[int] = None
    totalEngagements: Optional[int] = None
    totalLikes: Optional[int] = None
    totalComments: Optional[int] = None
    topPostType: Optional[str] = None
    totalMentions: Optional[int] = None


class PostEngagement(BaseModel):
    likes: int
    comments: int


class SummaryAndAchievement(BaseModel):
    summary: str
    achievements: List[str]


class ActivityOverviewAiResponse(BaseModel):
    topMediaType: str
    peakPostingTime: str


class ActivityOverview(ActivityOverviewAiResponse):
    averageLikes: Optional[Union[int, float]] = None
    averageComments: Optional[Union[int, float]] = None
    averageImpressionsPerPost: Optional[Union[int, float]] = None


class AIIndustryClassification(BaseModel):
    name: str
    text: str


class SuggestedImprovement(BaseModel):
    title: str
    text: str


class TopSuggestedImprovement(BaseModel):
    improvement: SuggestedImprovement
    priorityScore: int


class ReportModel(BaseModel):
    # — Core sections —
    accountInfo: AccountInfo
    overview: Overview
    highlights: Optional[List[str]] = None
    performanceMetrics: Optional[
        PerformanceMetrics
        | MultiAccReportGenericType[
            PerformanceMetrics, PerformanceMetrics, PerformanceMetrics
        ]
    ] = None
    kpiAnalysis: Optional[
        KPIAnalysis | MultiAccReportGenericType[KPIAnalysis, KPIAnalysis, KPIAnalysis]
    ] = None
    keyMetrics: Optional[
        KeyMetrics | MultiAccReportGenericType[KeyMetrics, KeyMetrics, KeyMetrics]
    ] = None
    aiRecommendation: Optional[List[str]] = None

    class Config:
        # Permit arbitrary extra fields (e.g. engagementOverTime, recentHashtags, etc.)
        extra = "allow"
