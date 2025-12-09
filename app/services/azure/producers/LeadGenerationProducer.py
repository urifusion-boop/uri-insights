"""
LeadGenerationProducer - Sends lead generation jobs to queue for async processing
"""
from typing import Dict, Any
from app.domain.enums.datasenderservices_enum import DataSenderServicesEnum
from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import LeadGenerationQueueMessageTypeEnum
from app.services.DataSenderService import DataSenderService


class LeadGenerationProducer:
    """Producer for sending lead generation jobs to queue"""

    @staticmethod
    async def send_lead_generation_job(
        lead_form_id: str,
        user_id: str,
        lead_form: Dict[str, Any]
    ):
        """
        Send a lead generation job to the queue for background processing.

        Args:
            lead_form_id: ID of the lead form
            user_id: User ID who triggered the generation
            lead_form: Complete lead form document with keywords, platforms, etc.
        """
        message_body = {
            "lead_form_id": lead_form_id,
            "user_id": user_id,
            "lead_form": lead_form
        }

        await DataSenderService.send_data(
            DataSenderServicesEnum.AZURE_SERVICE_BUS,
            QueueEnum.LEAD_GENERATION_QUEUE,  # type: ignore
            message_body,
            LeadGenerationQueueMessageTypeEnum.CONVERSATIONAL_LEAD_GENERATION
        )

        print(f"📤 Lead generation job queued for form {lead_form_id}")
