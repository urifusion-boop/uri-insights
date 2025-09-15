from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import FileImportQueueMessageTypeEnum
from app.services.LeadService import LeadService
from app.services.azure.AzureServiceBusConsumer import AzureServiceBusConsumer


class FileImportConsumer(AzureServiceBusConsumer):
    QUEUE_NAME = QueueEnum.FILE_IMPORT_QUEUE  # type: ignore

    def __init__(self):
        super().__init__(FileImportConsumer.QUEUE_NAME)

    async def handle_message(self, msg, message_type):
        match message_type:
            case FileImportQueueMessageTypeEnum.LEADS_IMPORT:
                await LeadService.process_imported_leads(str(msg))
            case FileImportQueueMessageTypeEnum.CONVERSATIONAL_LEADS_IMPORT:
                await LeadService.process_imported_leads(str(msg), True)
