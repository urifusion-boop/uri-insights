# Enums
from enum import Enum


class DateFilterEnum(Enum):
    LAST_24_HOURS = "24hr"
    LAST_3_DAYS = "3_days"
    LAST_7_DAYS = "7_days"
    LAST_1_WEEK = "1_week"
    LAST_2_WEEKS = "2_weeks"
    LAST_1_MONTH = "1_month"
    LAST_2_MONTHS = "2_months"
    LAST_3_MONTHS = "3_months"
