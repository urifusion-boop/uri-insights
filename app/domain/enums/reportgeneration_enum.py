from enum import Enum


class ReportGenerationTypeEnum(Enum):
    ACCOUNT_TRACKING = "ACCOUNT_TRACKING"
    LEAD_TRACKING = "LEAD_TRACKING"
    HASHTAG_TRACKING = "HASHTAG_TRACKING"
    KEYWORD_TRACKING = "KEYWORD_TRACKING"


class FacebookAccountKeysEnum(Enum):
    NAME = "name"
    FOLLOWERS_COUNT = "followers_count"
    FAN_COUNT = "fan_count"
    USERNAME = "username"
    LOCATION = "location"
    WEBSITE = "website"


class AccountTrackingKpiName(Enum):
    TOP_PERFORMING_HASHTAG = "Top Performing Hashtag"


class AccountTrackingIncludedFields(Enum):
    ENGAGEMENT_GRAPH = "engagement_graph"
    LATEST_POSTS = "latest_posts"
    AUDIENCE_LOCATION = "audience_location"
    SUMMARY_AND_ACHIEVEMENT = "summary_and_achievement"
    SUGGESTED_IMPROVMENT = "suggested_improvement"


class ReportGenSectionKeyEnum(Enum):
    ACCOUNT_INFO = "accountInfo"
    OVERVIEW = "overview"
    HIGHLIGHTS = "highlights"
    PERFORMANCE_METRICS = "performanceMetrics"
    KPI_ANALYSIS = "kpiAnalysis"
    KEY_METRICS = "keyMetrics"
    RECOMMENDATIONS = "ai_recommendations"

    # Account Tracking Report Gen sections
    ENGAGEMENT_OVER_TIME = "engagement_graph"
    LAST_25_POSTS = "latest_posts"
    AUDIENCE_LOCATION = "audience_location"
    MOST_USED_HASHTAGS = "mostUsedHashtags"
    SUMMARY_AND_ACHIEVEMENT = "summary_and_achievement"
    ACTIVITY_OVERVIEW = "activityOverview"
    AI_INDUSTRY_CLASSIFICATION = "aiIndustryClassification"
    TOP_SUGGESTED_IMPROVEMENT = "suggested_improvement"

    # Hashtag Tracking Report Gen sections
    ENGAGEMENTS_AND_LIKES = "mention_and_reach_graph"
    POST_TYPE_DISTRIBUTION = "post_type_distribution"
    HASHTAG_MENTIONS = "hashtag_mentions"
    RELATED_HASHTAGS = "related_hashtags"
    TRENDING_HASHTAGS = "trending_hashtags"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    RECENT_POSTS = "recent_posts"


class ReportGenSectionMethodsEnum(Enum):
    ACCOUNT_INFO = "get_account_info"
    OVERVIEW = "get_overview"
    HIGHLIGHTS = "get_highlights"
    PERFORMANCE_METRICS = "get_performance_metrics"
    KPI_ANALYSIS = "get_kpi_analysis"
    KEY_METRICS = "get_key_metrics"
    RECOMMENDATIONS = "get_ai_recommendations"

    # Account Tracking Report Gen Section Method Names
    ENGAGEMENT_OVER_TIME = "get_engagement_over_time"
    LAST_25_POSTS = "get_last_25_posts"
    AUDIENCE_LOCATION = "get_audience_location"
    MOST_USED_HASHTAGS = "get_most_used_hashtags"
    SUMMARY_AND_ACHIEVEMENT = "get_summary_and_achievement"
    ACTIVITY_OVERVIEW = "get_activity_overview"
    AI_INDUSTRY_CLASSIFICATION = "get_ai_industry_classification"
    TOP_SUGGESTED_IMPROVEMENT = "get_top_suggested_improvement"

    # Hashtag Tracking Report Gen Section Method Names
    ENGAGEMENTS_AND_LIKES = "get_engagements_and_likes"
    POST_TYPE_DISTRIBUTION = "get_post_type_distribution"
    HASHTAG_MENTIONS = "get_hashtag_mentions"
    RELATED_HASHTAGS = "get_related_hashtags"
    TRENDING_HASHTAGS = "get_trending_hashtags"
    SENTIMENT_ANALYSIS = "get_sentiment_analysis"
    RECENT_POSTS = "get_recent_posts"
