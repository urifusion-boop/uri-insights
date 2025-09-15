from enum import Enum


class InstagramMediaTypeEnum(Enum):
    IMAGE = "IMAGE"
    REELS = "REELS"


class InstagramMediaContainerStatusEnum(Enum):
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"
    FINISHED = "FINISHED"
    IN_PROGRESS = "IN_PROGRESS"
    PUBLISHED = "PUBLISHED"


class InstagramPeriodEnum(Enum):
    DAY = "day"
    LIFETIME = "lifetime"


class InstagramMetricTypeEnum(Enum):
    TIME_SERIES = "time_series"
    TOTAL_VALUE = "total_value"


class InstagramTimeFrameEnum(Enum):
    LAST_90_DAYS = "last_90_days"
    THIS_WEEK = "this_week"
    PREV_MONTH = "prev_month"
    THIS_MONTH = "this_month"
    LAST_30_DAYS = "last_30_days"
    LAST_14_DAYS = "last_14_days"
