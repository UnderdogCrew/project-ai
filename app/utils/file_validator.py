from fastapi import UploadFile
from typing import Tuple, Optional
import magic
import os

ALLOWED_IMAGE_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/svg': '.svg'
}

ALLOWED_DOCUMENT_TYPES = {
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/json': '.json'
}

async def validate_file(file: UploadFile) -> Tuple[bool, Optional[str], Optional[str]]:
    # Read first 2048 bytes for MIME detection
    first_chunk = await file.read(2048)
    # Reset file pointer
    await file.seek(0)
    
    mime_type = magic.from_buffer(first_chunk, mime=True)
    
    # Check if file is an image
    if mime_type in ALLOWED_IMAGE_TYPES:
        return True, "image", mime_type
    
    # Check if file is a document
    if mime_type in ALLOWED_DOCUMENT_TYPES:
        return True, "document", mime_type
    
    return False, None, mime_type

def get_file_extension(mime_type: str) -> str:
    if mime_type in ALLOWED_IMAGE_TYPES:
        return ALLOWED_IMAGE_TYPES[mime_type]
    return ALLOWED_DOCUMENT_TYPES.get(mime_type, '')