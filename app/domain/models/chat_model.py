from pydantic import BaseModel
from typing import List, Optional
from app.domain.enums.sentiment_enum import SentimentEnum
from app.domain.responses.reportgeneration_response import TopSuggestedImprovement


class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatModel(BaseModel):
    model: str = "gpt-4o-mini"
    messages: List[ChatMessage]
    temperature: float = 0.5


class EmbeddingModel(BaseModel):
    model: str = "text-embedding-ada-002"
    input: str


class ImageModel(BaseModel):
    model: str = "image-dalle"
    prompt: str
    n: int = 1
    size: str = "1024x1024"


class AudioModel(BaseModel):
    url: str


class PlainText(BaseModel):
    text: str


class InsightSummaryImprovementSuggestion(BaseModel):
    title: str
    description: str
    priority_score: str


class InsightSummaryPerformanceScore(BaseModel):
    title: str
    description: str
    score: str
    rating: str


class InsightSummaryPerformanceScoreBreakdown(BaseModel):
    performance_scores: List[InsightSummaryPerformanceScore]
    average_performance_score: str


class InsightSummaryActivityBreakdown(BaseModel):
    avg_likes: int
    avg_comments: int
    top_performing_media_type: str
    peak_posting_time: str
    engagement_trend: str


class InsightSummaryAchievements(BaseModel):
    summary: str
    achievements: List[str]


class TweetOptimizationResponse(BaseModel):
    optimal_length: str
    recommended_tones: List[str]
    effective_cta_phrases: List[str]
    common_patterns: List[str]


class EmotionalTone(BaseModel):
    tone: str  # e.g., "joy", "anger", etc.
    score: float  # Score of the tone


class ContentTheme(BaseModel):
    theme: str  # E.g., "sustainability", "innovation"
    mentions: int  # Number of times the theme is mentioned


class ConversationVelocity(BaseModel):
    growth_rate: float  # Growth rate in percentage
    peak_times: List[
        str
    ]  # List of peak times (e.g., ["2024-11-01 10:00", "2024-11-01 15:00"])


class WeeklyCampaignCalendar(BaseModel):
    topic: str
    title: str  # Growth rate in percentage
    post: str  # List of peak times (e.g., ["2024-11-01 10:00", "2024-11-01 15:00"])
    media_type: str
    day_of_the_week: str
    post_time: str
    hashtags: List[str]
    post_justification: str


class KeywordConversationInsight(BaseModel):
    key_trends: List[str]  # Summary of key conversation trends
    recommendations: List[str]  # Actionable business recommendations
    engagement_drivers: List[str]  # List of factors driving engagement
    engagement_opportunities: List[str]  # Suggestions to improve engagement
    emotional_tones: List[EmotionalTone]  # List of emotional tones with scores
    content_themes: List[ContentTheme]
    conversation_velocity: ConversationVelocity  # Conversation velocity metrics
    weekly_campaign_calendar: List[WeeklyCampaignCalendar]


class GeneratedLead(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    score: Optional[int] = None
    social_profile: str
    social_profile_link: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    industry: Optional[str] = None
    mention: Optional[str] = None
    summary_of_mention: Optional[str] = None
    interest_level: str  # High, Medium, or Low
    opportunity_type: str  # Sales, Recruitment, Partnership, or Other
    lead_reason: str  # Why this lead is relevant
    follow_up_message: str  # Personalized follow-up message
    follow_up_approach: str  # Best approach for following up (e.g., Email, LinkedIn)
    lead_source: Optional[str] = None
    lead_link: Optional[str] = None


class RegeneratedLeadFollowUpMessage(BaseModel):
    follow_up_message: str


class PostSentiment(BaseModel):
    id: str
    caption: str
    sentiment: SentimentEnum


class EngagementOverTime(BaseModel):
    post_id: str
    timestamp: str
    like_count: int
    comment_count: int


class PostEngagementSummary(BaseModel):
    id: str
    caption: str
    timestamp: str
    like_count: int
    comment_count: int


class HashtagInsightSummary(BaseModel):
    related_hashtags: List[str]
    trending_hashtags: List[str]
    total_mentions: int


class OverallSentiment(BaseModel):
    total_positive: int


class SentimentAnalysis(BaseModel):
    overall_sentiment: dict[str, float]
    post_sentiments: List[PostSentiment]


class IndustryClassification(BaseModel):
    industry_name: str
    overview: str


class InsightSummary(BaseModel):
    industry_classification: IndustryClassification
    improvement_suggestions: List[InsightSummaryImprovementSuggestion]
    performance_score_breakdown: InsightSummaryPerformanceScoreBreakdown
    activity_breakdown: InsightSummaryActivityBreakdown
    content_themes: List[ContentTheme]
    key_trends: List[str]
    engagement_drivers: List[str]  # List of factors driving engagement
    engagement_opportunities: List[str]  # Suggestions to improve engagement
    conversation_velocity: ConversationVelocity  # Conversation velocity metrics
    weekly_campaign_calendar: List[WeeklyCampaignCalendar]
    summary_and_achievements: InsightSummaryAchievements


class InsightSummaryPart1(BaseModel):
    industry_classification: IndustryClassification
    improvement_suggestions: List[InsightSummaryImprovementSuggestion]
    performance_score_breakdown: InsightSummaryPerformanceScoreBreakdown
    activity_breakdown: InsightSummaryActivityBreakdown
    content_themes: List[ContentTheme]
    key_trends: List[str]


class InsightSummaryPart2(BaseModel):
    engagement_drivers: List[str]  # List of factors driving engagement
    engagement_opportunities: List[str]  # Suggestions to improve engagement
    conversation_velocity: ConversationVelocity  # Conversation velocity metrics
    weekly_campaign_calendar: List[WeeklyCampaignCalendar]
    summary_and_achievements: InsightSummaryAchievements


class HashtagConversationInsight(BaseModel):
    key_trends: List[str]  # Summary of key conversation trends
    recommendations: List[str]  # Actionable business recommendations
    engagement_drivers: List[str]  # List of factors driving engagement
    engagement_opportunities: List[str]  # Suggestions to improve engagement
    emotional_tones: List[EmotionalTone]  # List of emotional tones with scores
    content_themes: List[ContentTheme]
    conversation_velocity: ConversationVelocity  # Conversation velocity metrics
    weekly_campaign_calendar: List[WeeklyCampaignCalendar]


class LeadBusinessSummary(BaseModel):
    summary: str


class LeadBusinessSummaryWithKeywords(LeadBusinessSummary):
    keywords: List[str]


class InstagramCommentKeyword(BaseModel):
    keyword: str


class ReportGenerationOverview(BaseModel):
    summary: str


class ReportGenerationHighlights(BaseModel):
    highlights: List[str]


class ReportGenerationGenericTextResult(BaseModel):
    text: str


class ReportGenerationFrequentHashtag(BaseModel):
    hashtag: str
    frequecy: int


class ReportGenerationFrequentHashtagsList(BaseModel):
    data: List[ReportGenerationFrequentHashtag]


class AIRecommendation(BaseModel):
    recommendations: List[str]


class TopSuggestedImprovementsList(BaseModel):
    data: List[TopSuggestedImprovement]


class SentimentResponse(BaseModel):
    score: float
    magnitude: float
    sentiment: str  # "positive", "neutral", or "negative"
