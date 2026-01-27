"""
LazarusMonitoringConsumer - Processes Lazarus monitoring scan jobs from Azure Service Bus queue
"""
import json
from azure.servicebus import ServiceBusReceivedMessage
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums.queue_enum import QueueEnum
from app.services.azure.AzureServiceBusConsumer import AzureServiceBusConsumer
from app.services.LazarusMonitoringService import LazarusMonitoringService
from app.services.azure.producers.LazarusMonitoringProducer import LazarusMonitoringProducer
from app.database import get_db


class LazarusMonitoringConsumer(AzureServiceBusConsumer):
    """
    Consumer that processes Lazarus monitoring scan jobs from LAZARUS_MONITORING_QUEUE.

    This runs as a separate worker process independent of the web server,
    preventing blocking issues during long-running monitoring scans.
    """

    QUEUE_NAME = QueueEnum.LAZARUS_MONITORING_QUEUE  # type: ignore

    def __init__(self):
        super().__init__(LazarusMonitoringConsumer.QUEUE_NAME)
        self.db: AsyncIOMotorDatabase | None = None

    async def setup(self):
        """Initialize consumer and database connection"""
        await super().setup()
        # Get database connection for this worker
        self.db = get_db()
        print(f"✅ LazarusMonitoringConsumer initialized with database connection")

    async def handle_message(self, msg: ServiceBusReceivedMessage, message_type: str):
        """
        Handle incoming Lazarus monitoring scan messages.

        Args:
            msg: Azure Service Bus message containing scan job data
            message_type: Type of message (should be LAZARUS_MONITORING_SCAN)
        """
        try:
            # Parse message body
            message_body = json.loads(str(msg))
            scan_type = message_body.get("scan_type")
            user_id = message_body.get("user_id")
            batch_size = message_body.get("batch_size", 100)

            print(f"📥 Processing Lazarus monitoring scan: {scan_type} (user: {user_id or 'all'})")

            # Route to appropriate handler based on message type
            if message_type == "LAZARUS_MONITORING_SCAN":
                await self._handle_monitoring_scan(
                    user_id=user_id,
                    batch_size=batch_size
                )
            else:
                print(f"⚠️ Unknown message type: {message_type}")

        except Exception as e:
            print(f"❌ Error processing Lazarus monitoring message: {str(e)}")
            import traceback
            traceback.print_exc()
            # Let Azure Service Bus handle retry logic via dead-letter queue
            raise

    async def _handle_monitoring_scan(
        self,
        user_id: str | None = None,
        batch_size: int = 100
    ):
        """
        Process Lazarus monitoring scan job.

        This runs the full monitoring pipeline:
        1. Scan focus contacts for job changes and buying signals
        2. Scan company monitors for hiring sprees and pivots
        3. Generate alerts for detected signals
        4. Re-queue next scan job
        """
        try:
            print(f"🔍 Starting Lazarus monitoring scan (batch_size: {batch_size})")

            # Scan focus contacts (individuals)
            focus_results = await LazarusMonitoringService.scan_focus_contacts(
                db=self.db,
                batch_size=batch_size
            )

            print(f"  ✅ Focus contacts: {focus_results['scanned']} scanned, {focus_results['alerts_created']} alerts")

            # Scan company monitors
            company_results = await LazarusMonitoringService.scan_company_monitors(
                db=self.db,
                batch_size=batch_size
            )

            print(f"  ✅ Company monitors: {company_results['scanned']} scanned, {company_results['alerts_created']} alerts")

            total_scanned = focus_results['scanned'] + company_results['scanned']
            total_alerts = focus_results['alerts_created'] + company_results['alerts_created']

            print(f"✅ Lazarus monitoring scan completed: {total_scanned} total scanned, {total_alerts} alerts")

            # Schedule next scan in 1 hour
            await LazarusMonitoringProducer.schedule_monitoring_scan(delay_hours=1)

        except Exception as e:
            print(f"❌ Error in Lazarus monitoring scan: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
