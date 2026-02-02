"""
LeadGenerationProducer - Sends lead generation jobs to queue for async processing
"""
from typing import Dict, Any
from datetime import datetime, timedelta
from app.domain.enums.datasenderservices_enum import DataSenderServicesEnum
from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import LeadGenerationQueueMessageTypeEnum
from app.services.DataSenderService import DataSenderService
from app.services.azure.AzureServiceBusProducer import producer as azure_producer


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

    @staticmethod
    async def schedule_lead_generation_job(
        lead_form_id: str,
        user_id: str,
        lead_form: Dict[str, Any],
        delay_hours: int
    ):
        """
        Schedule a lead generation job to run after a delay (for recurring monitoring).
        ONLY used for conversational leads with monitoring_interval_hours > 0.

        Args:
            lead_form_id: ID of the lead form
            user_id: User ID who triggered the generation
            lead_form: Complete lead form document with keywords, platforms, etc.
            delay_hours: Number of hours to wait before making the message available
        """
        message_body = {
            "lead_form_id": lead_form_id,
            "user_id": user_id,
            "lead_form": lead_form
        }

        # Calculate scheduled time (UTC)
        scheduled_time = datetime.utcnow() + timedelta(hours=delay_hours)

        # Use Azure Service Bus scheduled message feature
        await azure_producer.send_scheduled_message(
            queue_name=QueueEnum.LEAD_GENERATION_QUEUE.value,
            message_body=message_body,
            message_type=LeadGenerationQueueMessageTypeEnum.CONVERSATIONAL_LEAD_GENERATION.value,
            scheduled_enqueue_time_utc=scheduled_time
        )

        print(f"⏰ Scheduled lead generation job for form {lead_form_id} to run in {delay_hours} hour(s) at {scheduled_time} UTC")
