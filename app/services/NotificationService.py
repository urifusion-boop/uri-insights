import asyncio
import json
from typing import Optional
from app.domain.enums.datasenderservices_enum import DataSenderServicesEnum
from app.services.DataSenderService import DataSenderService
from app.services.azure.AzureServiceBusProducer import send_message
from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import (
    AlertQueueMessageTypeEnum,
    FileGenerationQueueMessageTypeEnum,
    LeadFormNotificationMessageTypeEnum,
    LeadManagementMessageTypeEnum,
    UserNotificationQueueMessageTypeEnum,
)
from app.core.helpers.notification_helper import NotificationHelper


class NotificationService:
    @staticmethod
    async def __send_async_notification(
        notification_data: Optional[dict],
        queue,
        alert_queue_message_type,
    ):
        if notification_data:
            await DataSenderService.send_data(
                DataSenderServicesEnum.AZURE_SERVICE_BUS,
                queue_name=queue,
                data=notification_data,
                message_type=alert_queue_message_type,
            )
        else:
            raise ValueError(
                f"Notification data is None for queue: {queue} and message type: {alert_queue_message_type}"
            )

    @staticmethod
    async def notify_new_lead(lead: dict, is_high_priority: bool):
        notification_data = await NotificationHelper.set_lead_alert_data(lead)
        queue = QueueEnum.LEAD_TRACKING_NOTIFICATION  # type: ignore[attr-defined]
        alert_queue_message_type = (
            AlertQueueMessageTypeEnum.HIGH_PRIORITY_LEAD
            if is_high_priority
            else AlertQueueMessageTypeEnum.NEW_LEAD_ALERT
        )

        await NotificationService.__send_async_notification(
            notification_data=notification_data,
            queue=queue,
            alert_queue_message_type=alert_queue_message_type,
        )

    @staticmethod
    async def notify_high_priority(mention: dict):
        notification_data = await NotificationHelper.set_mention_alert_data(mention)
        queue = QueueEnum.ALERT_NOTIFICATION  # type: ignore[attr-defined]
        alert_queue_message_type = AlertQueueMessageTypeEnum.HIGH_PRIORITY_MENTION

        await NotificationService.__send_async_notification(
            notification_data=notification_data,
            queue=queue,
            alert_queue_message_type=alert_queue_message_type,
        )

    @staticmethod
    async def notify_report_generation(
        data: dict,
        message_type: FileGenerationQueueMessageTypeEnum = FileGenerationQueueMessageTypeEnum.PERFORMANCE_REPORT,
    ):
        queue = QueueEnum.REPORT_NOTIFICATION  # type: ignore[attr-defined]
        await NotificationService.__send_async_notification(
            notification_data=data,
            queue=queue,
            alert_queue_message_type=message_type,
        )

    @staticmethod
    async def send_lead_notification(
        data: dict, message_type: UserNotificationQueueMessageTypeEnum
    ):
        await NotificationService.__send_async_notification(
            notification_data=data,
            queue=QueueEnum.USER_NOTIFICATION,  # type: ignore[attr-defined]
            alert_queue_message_type=message_type,
        )

    @staticmethod
    async def send_lead_form_notification(
        data: dict, message_type: LeadFormNotificationMessageTypeEnum
    ):
        await NotificationService.__send_async_notification(
            notification_data=data,
            queue=QueueEnum.LEAD_FORM_NOTIFICATION_QUEUE,  # type: ignore[attr-defined]
            alert_queue_message_type=message_type,
        )

    @staticmethod
    async def send_lead_management_message(
        data: dict, message_type: LeadManagementMessageTypeEnum
    ):
        await NotificationService.__send_async_notification(
            notification_data=data,
            queue=QueueEnum.LEAD_MANAGEMENT_QUEUE,  # type: ignore[attr-defined]
            alert_queue_message_type=message_type,
        )
