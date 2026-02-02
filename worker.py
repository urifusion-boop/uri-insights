"""
Worker Process for Azure Service Bus Queue Consumers

This is a standalone process that runs independently from the web server.
It consumes jobs from multiple Azure Service Bus queues and processes them in the background.

Queues:
    - LEAD_GENERATION_QUEUE: Conversational lead generation jobs
    - LAZARUS_MONITORING_QUEUE: Lazarus Protocol monitoring scans

Usage:
    python worker.py

Deployment:
    - Run as separate container/process alongside web server
    - Can scale horizontally (multiple worker instances)
    - Monitors multiple queues concurrently
"""
import asyncio
import signal
import sys
from app.services.azure.consumers.LeadGenerationConsumer import LeadGenerationConsumer
from app.services.azure.consumers.LazarusMonitoringConsumer import LazarusMonitoringConsumer
from app.database import connect_to_mongo
from app.core.config import settings


# Global consumer instances for graceful shutdown
lead_consumer_instance = None
lazarus_consumer_instance = None


async def main():
    """
    Main worker loop - initializes all consumers and keeps them running.
    """
    global lead_consumer_instance, lazarus_consumer_instance

    print("=" * 80)
    print("🚀 Multi-Queue Worker Starting...")
    print("=" * 80)
    print(f"Queues:")
    print(f"  1. LEAD_GENERATION_QUEUE → Conversational Lead Generation")
    print(f"  2. LAZARUS_MONITORING_QUEUE → Lazarus Protocol Scans")
    print("=" * 80)

    try:
        # Connect to MongoDB first (required before consumers can use get_db())
        print("🔌 Connecting to MongoDB...")
        connect_to_mongo(settings.MONGODB_DB)
        print("✅ MongoDB connected")

        # Create and initialize Lead Generation consumer
        print("🔧 Initializing Lead Generation Consumer...")
        lead_consumer_instance = LeadGenerationConsumer()
        await lead_consumer_instance._async_init()
        print("✅ Lead Generation Consumer ready")

        # Create and initialize Lazarus Monitoring consumer
        print("🔧 Initializing Lazarus Monitoring Consumer...")
        lazarus_consumer_instance = LazarusMonitoringConsumer()
        await lazarus_consumer_instance.setup()
        print("✅ Lazarus Monitoring Consumer ready")

        print("=" * 80)
        print("✅ All workers ready and listening for jobs...")
        print("Press Ctrl+C to stop")
        print("=" * 80)

        # Keep worker running indefinitely
        # Both consumers run in their own asyncio tasks
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
    Graceful shutdown - cleanup resources for all consumers.
    """
    global lead_consumer_instance, lazarus_consumer_instance

    print("\n" + "=" * 80)
    print("🛑 Shutting down all workers gracefully...")
    print("=" * 80)

    try:
        # Shutdown Lead Generation Consumer
        if lead_consumer_instance:
            await AzureServiceBusConsumer.shutdown()
            await lead_consumer_instance._cleanup()
            print("✅ Lead Generation Consumer stopped")

        # Shutdown Lazarus Monitoring Consumer
        if lazarus_consumer_instance:
            await lazarus_consumer_instance._cleanup()
            print("✅ Lazarus Monitoring Consumer stopped")

        print("=" * 80)
        print("✅ All workers shutdown complete")
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
