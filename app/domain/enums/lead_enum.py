# Enums
from enum import Enum


class LeadSourceEnum(str, Enum):
    REDDIT = "Reddit"
    FACEBOOK = "Facebook"
    INSTAGRAM = "Instagram"
    X = "X"
    TWITTER = "Twitter"
    LINKEDIN = "LinkedIn"
    TIKTOK = "Tiktok"
    NAIRALAND = "Nairaland"
    OTHER = "Other"


class LeadStatusEnum(str, Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    QUALIFIED = "Qualified"
    UNQUALIFIED = "Unqualified"
    CONVERTED = "Converted"


class LeadInterestLevelEnum(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class LeadOpportunityTypeEnum(str, Enum):
    SALES = "Sales"
    PARTNERSHIP = "Partnership"
    RECRUITMENT = "Recruitment"
    OTHER = "Other"


class LeadIndustryTypeEnum(str, Enum):
    ENERGY_UTILITIES = "Energy & Utilities"
    MANUFACTURING_INDUSTRIAL = "Manufacturing & Industrial"
    TECHNOLOGY_TELECOMMUNICATIONS = "Technology & Telecommunications"
    HEALTHCARE_PHARMACEUTICALS = "Healthcare & Pharmaceuticals"
    FINANCIAL_SERVICES = "Financial Services"
    RETAIL_CONSUMER_GOODS = "Retail & Consumer Goods"
    TRANSPORTATION_LOGISTICS = "Transportation & Logistics"
    REAL_ESTATE_CONSTRUCTION = "Real Estate & Construction"
    MEDIA_ENTERTAINMENT = "Media & Entertainment"
    AGRICULTURE_FOOD_INDUSTRY = "Agriculture & Food Industry"
    OTHER = "Other"


class LeadsProcessedStatus(str, Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    FAILED = "Failed"
