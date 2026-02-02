import asyncio
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus.management import ServiceBusAdministrationClient
from azure.servicebus import ServiceBusReceivedMessage
from app.core.config import settings

CONNECTION_STRING = settings.AZURE_SERVICE_BUS_CONNECTION_STRING


class AzureServiceBusConsumer:
    def __init__(self, queue_name: str):
        self.queue_name = queue_name

    consumer_task = None

    @classmethod
    async def create(cls):
        self = cls()
        await self._async_init()
        return self

    async def _async_init(self):
        await self.setup()
        AzureServiceBusConsumer.consumer_task = asyncio.create_task(
            self._consume_loop()
        )

        # Add exception handler to catch task failures
        def task_exception_handler(task):
            try:
                task.result()
            except Exception as e:
                print(f"❌ FATAL: Consumer task crashed with exception: {e}")
                import traceback
                traceback.print_exc()

        AzureServiceBusConsumer.consumer_task.add_done_callback(task_exception_handler)

    async def setup(self):
        self.service_bus_client = ServiceBusClient.from_connection_string(
            settings.AZURE_SERVICE_BUS_CONNECTION_STRING
        )
        self.admin_client = ServiceBusAdministrationClient.from_connection_string(
            settings.AZURE_SERVICE_BUS_CONNECTION_STRING
        )
        await self.create_queue(self.queue_name)

    @classmethod
    async def shutdown(cls):
        if cls.consumer_task:
            cls.consumer_task.cancel()
            try:
                await cls.consumer_task
            except asyncio.CancelledError:
                pass

    async def create_queue(self, queue_name: str):
        try:
            # Create queue if it doesn't exist
            if not self.admin_client.get_queue_runtime_properties(queue_name):
                self.admin_client.create_queue(queue_name)
                print(f"Queue {queue_name} created successfully.")
            else:
                print(f"Queue {queue_name} already exists.")

            # Get queue receiver
            self.receiver = self.service_bus_client.get_queue_receiver(queue_name)
        except Exception as e:
            print(f"Error creating queue: {e}")

    async def _consume_loop(self):
        print(f"🔄 Starting consume loop for {self.queue_name}...")
        try:
            while True:
                try:
                    print(f"📡 Connecting to Service Bus for {self.queue_name}...")
                    async with self.service_bus_client:
                        async with self.service_bus_client.get_queue_receiver(
                            self.queue_name,
                            prefetch_count=1  # Fetch only 1 message at a time (prevents duplicates across workers)
                        ) as receiver:
                            print(f"👂 Listening for messages on {self.queue_name}...")
                            async for msg in receiver:
                                message_type = msg.application_properties.get(
                                    b"messageType"
                                )
                                print(f"\n\nReceived from queue: {self.queue_name}")

                                # Start lock renewal task for long-running jobs
                                lock_renewal_task = None
                                try:
                                    # Renew lock every 30 seconds to prevent expiration during long jobs
                                    async def renew_lock():
                                        while True:
                                            await asyncio.sleep(30)
                                            try:
                                                await receiver.renew_message_lock(msg)
                                                print(f"🔄 Renewed message lock for {self.queue_name}")
                                            except Exception as e:
                                                print(f"⚠️ Failed to renew lock: {e}")
                                                break

                                    lock_renewal_task = asyncio.create_task(renew_lock())

                                    await self.handle_message(
                                        msg, message_type.decode("utf-8")
                                    )
                                except Exception as e:
                                    print(
                                        f"Error handling message from {self.queue_name}: {e}"
                                    )
                                finally:
                                    # Cancel lock renewal
                                    if lock_renewal_task:
                                        lock_renewal_task.cancel()
                                        try:
                                            await lock_renewal_task
                                        except asyncio.CancelledError:
                                            pass

                                    # Complete message to remove from queue
                                    try:
                                        await receiver.complete_message(msg)
                                    except Exception as complete_error:
                                        # If lock expired, message auto-returns to queue or completes
                                        # Don't crash the consumer
                                        print(f"⚠️ Could not complete message (likely lock expired): {complete_error}")
                except Exception as e:
                    print(f"Error in consuming from {self.queue_name}: {e}")
                    await asyncio.sleep(5)  # backoff before retry
        except asyncio.CancelledError:
            print(f"Consumer loop for {self.queue_name} cancelled.")
            raise
        finally:
            await self._cleanup()

    async def _cleanup(self):
        if self.service_bus_client:
            await self.service_bus_client.close()
            print(f"ServiceBusClient for {self.queue_name} closed.")

    async def handle_message(self, msg: ServiceBusReceivedMessage, message_type: str):
        raise NotImplementedError("Subclasses must implement `handle_message()`")
