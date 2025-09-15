from pydantic import BaseModel
from typing import List, Optional

from app.domain.enums.exporttype_enum import ExportTypeEnum
from app.domain.enums.filetype_enum import FileTypeEnum
from app.domain.enums.queue_message_type_enum import FileGenerationQueueMessageTypeEnum


class FileExportRequest(BaseModel):
    userId: str
    fileType: str = FileTypeEnum.PDF.value
    exportType: str = ExportTypeEnum.LEAD_DATA.value
    messageType: str = FileGenerationQueueMessageTypeEnum.GENERATE_FILE.value  # type: ignore[attr-defined]
    exportName: str
    data: Optional[List[dict]] = None

    class Config:
        use_enum_values = True
