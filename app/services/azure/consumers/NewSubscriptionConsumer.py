import asyncio
from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import LeadQueueMessageTypeEnum
from app.services.LeadFormService import LeadFormService
from app.services.azure.AzureServiceBusConsumer import AzureServiceBusConsumer


class NewSubscriptionConsumer(AzureServiceBusConsumer):
    QUEUE_NAME = QueueEnum.NEW_SUBSCRIPTION_QUEUE  # type: ignore

    def __init__(self):
        super().__init__(NewSubscriptionConsumer.QUEUE_NAME)

    async def handle_message(self, msg, message_type):
        match message_type:
            case LeadQueueMessageTypeEnum.LEAD:
                await LeadFormService.process_business_info_creation_from_service_bus(
                    str(msg)
                )
