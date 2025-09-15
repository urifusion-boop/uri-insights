from enum import Enum


class EndpointsEnum(Enum):
    SAVE_LINKEDIN_ACCOUNTS = "/linkedin-insights/save-linkedin-account"
    SAVE_INSTAGRAM_ACCOUNTS = "/instagram/save-instagram-account"
    SAVE_FACEBOOK_ACCOUNTS = "/facebook/save-facebook-account"
    KEYWORD_TRACKIING = "/keyword/create"
    HASHTAG_TRACKING = "/hashtag/create"
    CREATE_INFLUENCER = "/influencer/create"
    REPORT_GEN = "/report-generation/generate-report"
    ACCOUNT_TRACKING_REPORT_GEN = "/report/account-tracking/generate"
    HASHTAG_TRACKING_REPORT_GEN = "/report/hashtag-tracking/generate"
    INSIGHTS_ASSISTANT = "/ai-thread/create"
    SET_LEADS_AI_REPLY_CONTEXT = "/lead/ai-reply-context/update"
    LEAD_ENRICHMENT = "/lead/enrich"
    LEAD_ENRICHMENT_PHONE = "/lead/enrich/phone"
    LEAD_ENRICHMENT_EMAIL = "/lead/enrich/email"
    LEAD_GEN = "/lead/generate"


class UriBackendEndpointsEnum(Enum):
    URI_BACKEND_OAUTH_TOKEN = "/oauth/token"


class UriTaskManagerEndpointsEnum(Enum):
    GET_FEATURE_LIMIT = "/feature-limit/getByUserId"
