import asyncio
from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import LeadQueueMessageTypeEnum
from app.services.LeadService import LeadService
from app.services.azure.AzureServiceBusConsumer import AzureServiceBusConsumer


class LeadProcessorConsumer(AzureServiceBusConsumer):
    QUEUE_NAME = QueueEnum.LEAD_PROCESSING_QUEUE  # type: ignore

    def __init__(self):
        super().__init__(LeadProcessorConsumer.QUEUE_NAME)

    async def handle_message(self, msg, message_type):
        match message_type:
            case LeadQueueMessageTypeEnum.LEAD:
                await LeadService.process_lead_from_service_bus(str(msg))
