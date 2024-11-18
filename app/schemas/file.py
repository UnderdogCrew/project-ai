from pydantic import BaseModel, validator
from typing import Optional
from enum import Enum

class FileType(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    JSON = "json"

class FileUploadResponse(BaseModel):
    file_url: str
    file_type: FileType
    file_name: str
    file_size: int
    mime_type: str

class FileValidationError(BaseModel):
    detail: str