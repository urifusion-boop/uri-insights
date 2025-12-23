import asyncio
from typing import Optional, Union

from app.core.cache.manager.redis_manager import redis_manager
from app.domain.enums.datasenderservices_enum import DataSenderServicesEnum
from app.domain.enums.queue_enum import QueueEnum
from enum import Enum
from app.services.azure.AzureServiceBusProducer import producer


class DataSenderService:
    """
    A class to handle sending of data from uri-insights to third-party services
    e.g; Redis, Azure service bus
    """

    @staticmethod
    async def send_data(
        data_sender_service: DataSenderServicesEnum,
        queue_name: QueueEnum,
        data: Union[str, dict],
        message_type: Optional[Enum] = None,
    ):
        """Send data to a third party service's queue/bus"""
        match data_sender_service:
            case DataSenderServicesEnum.REDIS:
                await DataSenderService.__send_data_to_redis_queue(queue_name, data)
            case DataSenderServicesEnum.AZURE_SERVICE_BUS:
                if not message_type:
                    raise ValueError(
                        "Message type to send to azure service bus not provided"
                    )
                print("Sending data to azure service bus", queue_name, data)
                await DataSenderService.__send_data_to_azure_service_bus(
                    queue_name, data, message_type
                )

    @staticmethod
    async def __send_data_to_redis_queue(queue_name: QueueEnum, data: Union[str, dict]):
        redis_manager.enqueue(queue_name, data)

    @staticmethod
    async def __send_data_to_azure_service_bus(
        queue_name: QueueEnum,
        data: Union[str, dict],
        message_type: Enum,
    ):
        # Await the producer.send_message to ensure it completes and catch any errors
        await producer.send_message(
            queue_name,
            data,
            message_type.value,
        )
