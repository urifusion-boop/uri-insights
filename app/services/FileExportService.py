import asyncio
import json
from typing import Optional

from app.domain.enums.queue_enum import QueueEnum
from app.domain.requests.export_requests import FileExportRequest
from app.services.azure.AzureServiceBusProducer import send_message


class FileExportService:
    @staticmethod
    async def __send_async_export_request(
        export_data: Optional[dict],
        queue,
        file_generation_queue_message_type,
    ):
        if export_data:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    send_message(
                        queue,
                        json.dumps(export_data),  # Convert dict to JSON string
                        file_generation_queue_message_type,
                    )
                )
            except RuntimeError:
                # If no running event loop, create a new one (for scripts)
                asyncio.run(
                    send_message(
                        queue,
                        json.dumps(export_data),  # Convert dict to JSON string
                        file_generation_queue_message_type,
                    )
                )

    @staticmethod
    async def export_file_data(file_export_request: FileExportRequest):
        if file_export_request.data:
            export_data = file_export_request.dict(exclude_none=True)
            queue = QueueEnum.FILE_GENERATION  # type: ignore[attr-defined]

            await FileExportService.__send_async_export_request(
                export_data=export_data,
                queue=queue,
                file_generation_queue_message_type=export_data.get("messageType"),
            )
        else:
            raise ValueError("No data to export")
