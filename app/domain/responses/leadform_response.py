from pydantic import BaseModel


class AiInferredDescription(BaseModel):
    text: str
