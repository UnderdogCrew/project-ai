import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
import uuid
from app.core.config import settings
from typing import Optional

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.AWS_S3_BUCKET
        self.region = settings.AWS_REGION

    async def upload_file(
        self, 
        file: UploadFile, 
        folder: str,
        file_extension: str
    ) -> Optional[str]:
        try:
            file_key = f"{folder}/{str(uuid.uuid4())}{file_extension}"
            # Upload file to S3
            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                file_key
            )
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"
            return url
        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            return None