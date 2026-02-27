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
    PERSON_SEARCH_CREATE = "/lead-forms/person-search/create"
    ORGANIZATION_SEARCH_CREATE = "/lead-forms/organization-search/create"
    BUSINESS_SEARCH_CREATE = "/lead-forms/business-search/create"
    GOOGLE_MAPS_SEARCH_CREATE = "/lead-forms/google-maps-search/create"
    PERSON_SEARCH_UPDATE = "/lead-forms/person-search/update"
    ORGANIZATION_SEARCH_UPDATE = "/lead-forms/organization-search/update"
    BUSINESS_SEARCH_UPDATE = "/lead-forms/business-search/update"
    GOOGLE_MAPS_SEARCH_UPDATE = "/lead-forms/google-maps-search/update"


class UriBackendEndpointsEnum(Enum):
    URI_BACKEND_OAUTH_TOKEN = "/oauth/token"
    TRIAL_USAGE_INCREMENT = "/api/v1/trial/usage/increment"


class UriTaskManagerEndpointsEnum(Enum):
    GET_FEATURE_LIMIT = "/feature-limit/getByUserId"
