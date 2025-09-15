from pydantic import BaseModel

class MetaBatchRequestData(BaseModel):
    method: str
    relative_url: str