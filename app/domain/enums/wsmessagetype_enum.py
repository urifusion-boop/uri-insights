from enum import Enum


class WsMessageTypeEnum(str, Enum):
    NEW_LEAD = "NEW_LEAD"
    LEAD_GENERATION_COMPLETE = "LEAD_GENERATION_COMPLETE"
