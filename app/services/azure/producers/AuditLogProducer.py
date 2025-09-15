from typing import Any, Dict

from app.domain.enums.datasenderservices_enum import DataSenderServicesEnum
from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import AuditLogQueueMessageTypeEnum
from app.services.DataSenderService import DataSenderService


class AuditLogQueueProducerService:
    @staticmethod
    async def publish_audit_log(
        audit_data: Dict[str, Any], message_type: AuditLogQueueMessageTypeEnum
    ) -> None:
        try:
            await DataSenderService.send_data(
                DataSenderServicesEnum.AZURE_SERVICE_BUS,
                QueueEnum.AUDIT_LOG,  # type: ignore[attr-defined]
                audit_data,  # Data should be a dict
                message_type,
            )
        except Exception as e:
            print(f"Error publishing audit log ({message_type}): {str(e)}")
