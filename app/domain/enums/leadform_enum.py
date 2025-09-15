from enum import Enum


class LeadFormTypeEnum(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    CONVERSATIONAL = "CONVERSATIONAL"
    BUSINESS = "BUSINESS"


class PartnershipTypeEnum(str, Enum):
    STRATEGIC_ALLIANCE = "STRATEGIC_ALLIANCE"
    JOINT_VENTURE = "JOINT_VENTURE"
    DISTRIBUTOR = "DISTRIBUTOR"
    RESELLER = "RESELLER"
    TECHNOLOGY = "TECHNOLOGY"
    MARKETING = "MARKETING"
    ANY = "ANY"


class BusinessTypeEnum(str, Enum):
    STARTUP = "STARTUP"
    SME = "SME"
    ENTERPRISE = "ENTERPRISE"
    NON_PROFIT = "NON_PROFIT"
    GOVERNMENT = "GOVERNMENT"
    FREELANCER = "FREELANCER"
    ANY = "ANY"


class LeadFormDisabledReasonEnum(str, Enum):
    MAX_PAGE_REACHED = "All available data for this search on Apollo has been accessed."


class ConversationalFormIntentTypeEnum(str, Enum):
    LEAD_GENERATION = "Lead Generation"
    COMPETITOR_TRACKING = "Competitor Tracking"
    MARKET_INSIGHTS = "Market Insights"
    BRAND_AWARENESS = "Brand Awareness"


class AiLeadResponseGuidePlaybookEnum(str, Enum):
    LEAD_GENERATION = "Lead Generation"
    COMPETITOR_TRACKING = "Competitor Tracking"
    MARKET_INSIGHTS = "Market Insights"
    BRAND_AWARENESS = "Brand Awareness"
    CUSTOM = "CUSTOM"
