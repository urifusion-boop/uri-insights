# Enums
from enum import Enum


class NotificationSubjectEnum(str, Enum):
    NEW_LEAD = "New Lead Alert"
    HIGH_PRIORITY_MENTION = "High Priority Mention"
