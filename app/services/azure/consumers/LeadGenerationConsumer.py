"""
LeadGenerationConsumer - Processes lead generation jobs from Azure Service Bus queue
"""
import json
from azure.servicebus import ServiceBusReceivedMessage
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import LeadGenerationQueueMessageTypeEnum
from app.services.azure.AzureServiceBusConsumer import AzureServiceBusConsumer
from app.services.ConversationalLeadJobService import ConversationalLeadJobService
from app.database import get_db


class LeadGenerationConsumer(AzureServiceBusConsumer):
    """
    Consumer that processes lead generation jobs from LEAD_GENERATION_QUEUE.

    This runs as a separate worker process independent of the web server,
    preventing blocking issues during long-running lead generation tasks.
    """

    QUEUE_NAME = QueueEnum.LEAD_GENERATION_QUEUE  # type: ignore

    def __init__(self):
        super().__init__(LeadGenerationConsumer.QUEUE_NAME)
        self.db: AsyncIOMotorDatabase | None = None

    async def setup(self):
        """Initialize consumer and database connection"""
        await super().setup()
        # Get database connection for this worker
        self.db = get_db()
        print(f"✅ LeadGenerationConsumer initialized with database connection")

    async def handle_message(self, msg: ServiceBusReceivedMessage, message_type: str):
        """
        Handle incoming lead generation job messages.

        Args:
            msg: Azure Service Bus message containing job data
            message_type: Type of message (should be CONVERSATIONAL_LEAD_GENERATION)
        """
        try:
            # Parse message body
            message_body = json.loads(str(msg))
            lead_form_id = message_body.get("lead_form_id")
            user_id = message_body.get("user_id")
            lead_form = message_body.get("lead_form")
            # job_id is inside lead_form, not at top level
            job_id = lead_form.get("job_id") if lead_form else None

            print(f"📥 Processing lead generation job: {job_id} for form {lead_form_id}")

            # Route to appropriate handler based on message type
            if message_type == LeadGenerationQueueMessageTypeEnum.CONVERSATIONAL_LEAD_GENERATION.value:
                await self._handle_conversational_lead_generation(
                    lead_form_id=lead_form_id,
                    user_id=user_id,
                    lead_form=lead_form,
                    job_id=job_id
                )
            else:
                print(f"⚠️ Unknown message type: {message_type}")

        except Exception as e:
            print(f"❌ Error processing lead generation message: {str(e)}")
            import traceback
            traceback.print_exc()
            # Let Azure Service Bus handle retry logic via dead-letter queue
            raise

    async def _handle_conversational_lead_generation(
        self,
        lead_form_id: str,
        user_id: str,
        lead_form: dict,
        job_id: str | None = None
    ):
        """
        Process sales signal generation job.

        This runs the full lead generation pipeline:
        1. Fetch leads from social media platforms (Twitter, Facebook, TikTok)
        2. Apply filters (time range, location)
        3. Analyze with LLM for intent scoring
        4. Save qualified leads to database
        5. Update job status
        """
        try:
            print(f"🚀 Starting sales signal generation for form {lead_form_id}")

            # Run the full lead generation pipeline
            stats = await ConversationalLeadJobService.fetch_leads_from_platforms(
                db=self.db,
                lead_form=lead_form,
                user_id=user_id,
                job_id=job_id
            )

            print(f"✅ Lead generation completed for job {job_id}")
            print(f"   Stats: {stats}")

        except Exception as e:
            print(f"❌ Error in sales signal generation: {str(e)}")
            import traceback
            traceback.print_exc()

            # Update job status to failed
            if job_id:
                try:
                    from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository
                    await LeadGenerationJobRepository.update_job(
                        db=self.db,
                        job_id=job_id,
                        status="failed",
                        progress=0,
                        error=str(e)
                    )
                except Exception as update_error:
                    print(f"⚠️ Failed to update job status: {update_error}")

            # Re-raise to trigger Azure Service Bus retry
            raise
