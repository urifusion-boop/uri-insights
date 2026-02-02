import json
from fastapi import FastAPI
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.servicebus.management import ServiceBusAdministrationClient
from app.core.config import settings
import asyncio

app = FastAPI()

CONNECTION_STRING = settings.AZURE_SERVICE_BUS_CONNECTION_STRING


class AzureServiceBusProducer:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.service_bus_client = ServiceBusClient.from_connection_string(
            connection_string
        )
        self.admin_client = ServiceBusAdministrationClient.from_connection_string(
            connection_string
        )

    async def create_queue(self, queue_name: str):
        try:
            # Ensuring async behavior with FastAPI
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._sync_create_queue, queue_name)
        except Exception as e:
            print(f"Error creating queue: {e}")

    def _sync_create_queue(self, queue_name: str):
        """Helper function to call sync Azure admin client"""
        try:
            if not self.admin_client.get_queue_runtime_properties(queue_name):
                self.admin_client.create_queue(queue_name)
                print(f"Queue {queue_name} created successfully.")
            else:
                print(f"Queue {queue_name} already exists.")
        except Exception as e:
            print(f"Error creating queue: {e}")

    async def send_message(
        self,
        queue_name: str,
        message_body: dict,
        message_type: str = "default",
    ):
        # Create a fresh client for each send to avoid connection reuse issues
        async with ServiceBusClient.from_connection_string(self.connection_string) as client:
            sender = client.get_queue_sender(queue_name=queue_name)
            async with sender:
                # Ensure message body is a JSON string
                message_body_json = (
                    message_body
                    if isinstance(message_body, str)
                    else json.dumps(message_body)
                )

                message = ServiceBusMessage(
                    body=message_body_json,
                    application_properties={"messageType": message_type},
                    content_type="application/json",
                )

                try:
                    await sender.send_messages(message)
                    print(f"Sent message to queue: {queue_name}")
                except Exception as e:
                    print(f"Failed to send message: {e}")

    async def send_scheduled_message(
        self,
        queue_name: str,
        message_body: dict,
        message_type: str = "default",
        scheduled_enqueue_time_utc = None,
    ):
        """
        Send a scheduled message to the queue.
        The message will be available for processing only after scheduled_enqueue_time_utc.

        Args:
            queue_name: Name of the queue
            message_body: Message payload (dict)
            message_type: Message type for routing
            scheduled_enqueue_time_utc: datetime object in UTC when message should be available
        """
        # Create a fresh client for each send to avoid connection reuse issues
        async with ServiceBusClient.from_connection_string(self.connection_string) as client:
            sender = client.get_queue_sender(queue_name=queue_name)
            async with sender:
                # Ensure message body is a JSON string
                message_body_json = (
                    message_body
                    if isinstance(message_body, str)
                    else json.dumps(message_body)
                )

                message = ServiceBusMessage(
                    body=message_body_json,
                    application_properties={"messageType": message_type},
                    content_type="application/json",
                )

                try:
                    if scheduled_enqueue_time_utc:
                        # Use Azure Service Bus scheduled message feature
                        # Message will be invisible to workers until scheduled_enqueue_time_utc
                        sequence_numbers = await sender.schedule_messages(
                            messages=[message],
                            schedule_time_utc=scheduled_enqueue_time_utc
                        )
                        print(f"✅ Scheduled message to queue '{queue_name}' at {scheduled_enqueue_time_utc} (sequence: {sequence_numbers})")
                    else:
                        # No schedule time provided, send immediately
                        await sender.send_messages(message)
                        print(f"✅ Sent immediate message to queue: {queue_name}")
                except Exception as e:
                    print(f"❌ Failed to send scheduled message: {e}")
                    raise


producer = AzureServiceBusProducer(CONNECTION_STRING)


@app.post("/send/{queue_name}")
async def send_message(
    queue_name: str,
    message_body: dict,
    message_type: str = "default",
):
    """Send message asynchronously while ensuring queue exists"""
    try:
        # await producer.create_queue(queue_name)
        await producer.send_message(queue_name, message_body, message_type)

        print({"status": "Message sent successfully"})
        return {"status": "Message sent successfully"}
    except Exception as e:
        print("Exception occurred in sending azure message: ", e)
