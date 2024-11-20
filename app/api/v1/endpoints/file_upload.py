from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from typing import Optional
from app.utils.file_validator import validate_file, get_file_extension
from app.services.s3 import S3Service
from app.schemas.file import FileUploadResponse, FileType
from app.core.auth_middlerware import JWTBearer
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.core.config import settings

router = APIRouter()
s3_service = S3Service()

@router.post("/", dependencies=[Depends(JWTBearer())], response_model=FileUploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncIOMotorClient = Depends(get_database)
):
    payload = request.state.jwt_payload

    # Check for active user
    user = await db[settings.MONGODB_DB_NAME]["users"].find_one(
        {"email": payload['email'], "status": "ACTIVE"}
    )

    # Validate file
    is_valid, file_type, mime_type = await validate_file(file)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {mime_type}"
        )
    
    # Get user ID
    user_id = str(user["_id"])

    # Get file extension
    file_extension = get_file_extension(mime_type)
    
    # Determine folder based on file type
    folder = f"{user_id}/{file_type}s"
    
    # Upload to S3
    file_url = await s3_service.upload_file(
        file=file,
        folder=folder,
        file_extension=file_extension
    )
    
    if not file_url:
        raise HTTPException(
            status_code=500,
            detail="Failed to upload file"
        )
    
    return FileUploadResponse(
        file_url=file_url,
        file_type=FileType(file_type),
        file_name=file.filename,
        file_size=file.size,
        mime_type=mime_type
    )