"""
LazarusMonitoringProducer - Sends Lazarus monitoring jobs to queue for async processing
"""
from typing import Optional
from datetime import datetime, timedelta
from app.domain.enums.datasenderservices_enum import DataSenderServicesEnum
from app.domain.enums.queue_enum import QueueEnum
from app.services.DataSenderService import DataSenderService
from app.services.azure.AzureServiceBusProducer import producer as azure_producer


class LazarusMonitoringProducer:
    """Producer for sending Lazarus monitoring scan jobs to queue"""

    @staticmethod
    async def queue_monitoring_scan(
        user_id: Optional[str] = None,
        batch_size: int = 100
    ):
        """
        Queue a Lazarus monitoring scan job for immediate processing.

        Args:
            user_id: Optional user ID to scan only that user's monitors (for testing)
            batch_size: Number of monitors to scan per batch
        """
        message_body = {
            "scan_type": "full_scan",
            "user_id": user_id,
            "batch_size": batch_size,
            "queued_at": datetime.utcnow().isoformat()
        }

        await DataSenderService.send_data(
            DataSenderServicesEnum.AZURE_SERVICE_BUS,
            QueueEnum.LAZARUS_MONITORING_QUEUE,  # type: ignore
            message_body,
            "LAZARUS_MONITORING_SCAN"
        )

        print(f"📤 Lazarus monitoring scan job queued (user: {user_id or 'all'})")

    @staticmethod
    async def schedule_monitoring_scan(delay_hours: int = 1):
        """
        Schedule a Lazarus monitoring scan to run after a delay.
        Used for recurring scans (e.g., check every hour for monitors due for scanning).

        Args:
            delay_hours: Number of hours to wait before running the scan
        """
        message_body = {
            "scan_type": "scheduled_scan",
            "batch_size": 100,
            "queued_at": datetime.utcnow().isoformat()
        }

        # Calculate scheduled time (UTC)
        scheduled_time = datetime.utcnow() + timedelta(hours=delay_hours)

        # Use Azure Service Bus scheduled message feature
        await azure_producer.send_scheduled_message(
            queue_name=QueueEnum.LAZARUS_MONITORING_QUEUE.value,
            message_body=message_body,
            message_type="LAZARUS_MONITORING_SCAN",
            scheduled_enqueue_time_utc=scheduled_time
        )

        print(f"⏰ Scheduled Lazarus monitoring scan to run in {delay_hours} hour(s) at {scheduled_time} UTC")
