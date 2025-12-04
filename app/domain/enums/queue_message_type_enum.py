from enum import Enum


class AlertQueueMessageTypeEnum(Enum):
    NEGATIVE_ALERT_REPORT = "NEGATIVE_ALERT_REPORT"
    NEW_LEAD_ALERT = "NEW_LEAD_ALERT"
    HIGH_PRIORITY_MENTION = "HIGH_PRIORITY_MENTION"
    HIGH_PRIORITY_LEAD = "HIGH_PRIORITY_LEAD"


class LeadQueueMessageTypeEnum(Enum):
    LEAD = "LEAD"


class FileGenerationQueueMessageTypeEnum(Enum):
    GENERATE_FILE = "GENERATE_FILE"
    PERFORMANCE_REPORT = "PERFORMANCE_REPORT"
    PERFORMANCE_REPORT_ERROR = "PERFORMANCE_REPORT_ERROR"


class UserNotificationQueueMessageTypeEnum(Enum):
    EMPTY_APOLLO_SEARCH_RESULT = "EMPTY_APOLLO_SEARCH_RESULT"
    APOLLO_PAGINATION_END = "APOLLO_PAGINATION_END"
    LEADS_GENERATED_SUCCESSFULLY = "LEADS_GENERATED_SUCCESSFULLY"
    DUPLICATE_LEADS_FOUND = "DUPLICATE_LEADS_FOUND"


class NewSubscriptionQueueMessageTypeEnum(Enum):
    USER_SUBSCRIBED = "USER_SUBSCRIBED"


class FileImportQueueMessageTypeEnum(str, Enum):
    LEADS_IMPORT = "LEADS_IMPORT"
    CONVERSATIONAL_LEADS_IMPORT = "CONVERSATIONAL_LEADS_IMPORT"


class ExceptionLogQueueMessageTypeEnum(Enum):
    EXCEPTION_LOG = "EXCEPTION_LOG"


class AuditLogQueueMessageTypeEnum(Enum):
    USER_ACTIVITY = "USER_ACTIVITY"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class LeadManagementMessageTypeEnum(Enum):
    DELETED_LEAD = "DELETED_LEAD"


class LeadFormNotificationMessageTypeEnum(Enum):
    LEAD_REQUEST = "LEAD_REQUEST"


class LeadGenerationQueueMessageTypeEnum(Enum):
    """Message types for async lead generation jobs"""
    CONVERSATIONAL_LEAD_GENERATION = "CONVERSATIONAL_LEAD_GENERATION"


# Alias for backwards compatibility
QueueMessageTypeEnum = LeadGenerationQueueMessageTypeEnum
