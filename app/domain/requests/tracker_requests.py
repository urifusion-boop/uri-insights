from pydantic import BaseModel


class TrackerFilterRequest(BaseModel):
    inserted_id: str
    keyword: str
    tracker_type: int
    platform: str
