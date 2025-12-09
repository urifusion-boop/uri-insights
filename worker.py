"""
Worker Process for Lead Generation Queue Consumer

This is a standalone process that runs independently from the web server.
It consumes jobs from the Azure Service Bus LEAD_GENERATION_QUEUE and
processes them in the background.

Usage:
    python worker.py

Deployment:
    - Run as separate container/process alongside web server
    - Can scale horizontally (multiple worker instances)
    - Monitors LEAD_GENERATION_QUEUE for new jobs
"""
import asyncio
import signal
import sys
from app.services.azure.consumers.LeadGenerationConsumer import LeadGenerationConsumer
from app.database import connect_to_mongo
from app.core.config import settings


# Global consumer instance for graceful shutdown
consumer_instance = None


async def main():
    """
    Main worker loop - initializes consumer and keeps it running.
    """
    global consumer_instance

    print("=" * 80)
    print("🚀 Lead Generation Worker Starting...")
    print("=" * 80)
    print(f"Queue: LEAD_GENERATION_QUEUE")
    print(f"Message Types: CONVERSATIONAL_LEAD_GENERATION")
    print("=" * 80)

    try:
        # Connect to MongoDB first (required before consumer can use get_db())
        print("🔌 Connecting to MongoDB...")
        connect_to_mongo(settings.MONGODB_DB)
        print("✅ MongoDB connected")

        # Create and initialize consumer
        consumer_instance = LeadGenerationConsumer()
        await consumer_instance._async_init()

        print("✅ Worker ready and listening for jobs...")
        print("Press Ctrl+C to stop")
        print("=" * 80)

        # Keep worker running indefinitely
        # The consumer runs in its own asyncio task (consumer_task)
        await asyncio.Event().wait()  # Wait forever

    except KeyboardInterrupt:
        print("\n⚠️ Received shutdown signal (Ctrl+C)")
        await shutdown()
    except Exception as e:
        print(f"\n❌ Fatal error in worker: {str(e)}")
        import traceback
        traceback.print_exc()
        await shutdown()
        sys.exit(1)


async def shutdown():
    """
    Graceful shutdown - cleanup resources.
    """
    global consumer_instance

    print("\n" + "=" * 80)
    print("🛑 Shutting down worker gracefully...")
    print("=" * 80)

    try:
        if consumer_instance:
            # Cancel consumer task
            await AzureServiceBusConsumer.shutdown()
            print("✅ Consumer stopped")

            # Cleanup Azure Service Bus connections
            await consumer_instance._cleanup()
            print("✅ Connections closed")

        print("=" * 80)
        print("✅ Worker shutdown complete")
        print("=" * 80)

    except Exception as e:
        print(f"⚠️ Error during shutdown: {str(e)}")


def handle_signal(signum, frame):
    """
    Handle termination signals (SIGTERM, SIGINT) for graceful shutdown.
    """
    print(f"\n⚠️ Received signal {signum}")
    asyncio.create_task(shutdown())
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)   # Ctrl+C
    signal.signal(signal.SIGTERM, handle_signal)  # Docker stop, kill command

    # Import here to avoid circular imports
    from app.services.azure.AzureServiceBusConsumer import AzureServiceBusConsumer

    # Run the worker
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Worker stopped")
        sys.exit(0)
