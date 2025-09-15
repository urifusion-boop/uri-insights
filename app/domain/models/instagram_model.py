from pydantic import BaseModel

class InstagramBatchRequestData(BaseModel):
    method: str
    relative_url: str