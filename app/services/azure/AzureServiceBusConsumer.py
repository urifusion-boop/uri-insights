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
        try:
            print(f"🔄 Starting consume loop for {self.queue_name}...")
            async with self.service_bus_client:
                print(f"✅ Service Bus client connected for {self.queue_name}")

                # Keep worker alive and continuously reconnect to listen for messages
                while True:
                    try:
                        # Create receiver with proper settings to prevent duplicate processing
                        async with self.service_bus_client.get_queue_receiver(
                            queue_name=self.queue_name,
                            max_wait_time=60,  # Wait up to 60 seconds for messages
                            prefetch_count=0   # Process one message at a time (prevents duplicates across workers)
                        ) as receiver:
                            print(f"📡 Receiver ready for {self.queue_name}, listening...")
                            print(f"   Settings: max_wait_time=60s, prefetch_count=0 (ensures each worker gets unique messages)")

                            # Continuously listen for messages
                            async for msg in receiver:
                                message_type = msg.application_properties.get(b"messageType")
                                print(f"\n📩 Received message from queue: {self.queue_name}")
                                print(f"   Message Type: {message_type.decode('utf-8') if message_type else 'None'}")

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

                                    print(f"✅ Successfully processed message from {self.queue_name}")

                                except Exception as e:
                                    print(f"❌ Error handling message from {self.queue_name}: {e}")
                                    import traceback
                                    traceback.print_exc()
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
                                        print(f"✅ Message completed and removed from queue: {self.queue_name}")
                                    except Exception as complete_error:
                                        # If lock expired, message auto-returns to queue or completes
                                        # Don't crash the consumer
                                        print(f"⚠️ Could not complete message (likely lock expired): {complete_error}")

                            # When async for exits (no more messages), log and reconnect
                            print(f"⏸️ No messages available, reconnecting receiver in 5 seconds...")
                            await asyncio.sleep(5)

                    except Exception as receiver_error:
                        print(f"❌ Receiver error for {self.queue_name}: {receiver_error}")
                        await asyncio.sleep(5)  # Backoff before reconnecting

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
