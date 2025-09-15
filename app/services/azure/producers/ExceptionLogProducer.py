from typing import Any, Dict

from app.domain.enums.datasenderservices_enum import DataSenderServicesEnum
from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import ExceptionLogQueueMessageTypeEnum
from app.services.DataSenderService import DataSenderService


class ExceptionLogQueueProducerService:
    @staticmethod
    async def publish_exception_log(
        exception_data: Dict[str, Any],
    ) -> None:
        try:
            await DataSenderService.send_data(
                DataSenderServicesEnum.AZURE_SERVICE_BUS,
                QueueEnum.EXCEPTION_LOG,  # type: ignore[attr-defined]
                exception_data,  # Data should be a dict
                ExceptionLogQueueMessageTypeEnum.EXCEPTION_LOG,
            )
        except Exception as e:
            print(
                f"Error publishing exception log ({ExceptionLogQueueMessageTypeEnum.EXCEPTION_LOG}): {str(e)}"
            )
