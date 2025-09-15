from bson import ObjectId
from pydantic import Field
from app.domain.schemas.leadform_schema import LeadFormBase


class LeadFormSnapshot(LeadFormBase):
    lead_form_snapshot_id: str = Field(default_factory=lambda: str(ObjectId()))
