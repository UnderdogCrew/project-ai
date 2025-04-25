from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.core.config import settings
from datetime import datetime
from openai import OpenAI
from app.schemas.image_generation import ImageGenerationRequest, ImageGenerationResponse
import base64
import requests
import os, sys
from app.core.config import settings
import boto3
import uuid

router = APIRouter()
client = OpenAI(api_key=settings.OPENAI_API_KEY)


s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
        )
bucket_name = settings.AWS_S3_BUCKET
region = settings.AWS_REGION


@router.post("/", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    db: AsyncIOMotorClient = Depends(get_database),
):
    """
    Generate an image from text using DALL-E 3
    
    Parameters:
    - text: Text prompt for image generation
    
    Returns:
    - url: Generated image URL
    - message: Status message
    
    Raises:
    - 422: If request body or text is missing
    - 500: For internal server errors
    """
    filepath = ""
    image_path = ""
    file_url = ""
    try:
        
        # Generate image using DALL-E 3
        prompt = """
            Generate a image.
        """

        if request.art is not None:
            if request.art != "":
                prompt = f"Convert Image to {request.art} Style Image"

        image_url = request.url

        # Extract image name from URL
        image_name = image_url.split("/")[-1]  # -> "3e42169a-149c-4fd1-a001-ef76660c1842.jpeg"

        # Define local folder to save
        filepath = os.path.join(image_name)

        # Extract file extension
        _, file_extension = os.path.splitext(image_name)  # e.g. (name, ".jpeg")
        print(f"File extension: {file_extension}")

        # Download and save the image
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Image saved to {filepath}")
        else:
            print(f"Failed to download image. Status code: {response.status_code}")


        if request.feeling is not None:
            if request.feeling != "":
                prompt += f" with Feeling: {request.feeling}"
        
        print(prompt)
        # response = client.images.edit(
        #     model="gpt-image-1",
        #     prompt=prompt,
        #     image=open(filepath, "rb"),
        #     size="1024x1024",
        #     # quality="medium",
        #     n=1,
        # )
        # print(response.usage)
        # image_base64 = response.data[0].b64_json
        # image_bytes = base64.b64decode(image_base64)

        # Define local folder to save
        # image_path = os.path.join(f"{int(datetime.now().timestamp())}_{image_name}")

        # Save the image to a file
        # with open(f"{image_path}", "wb") as f:
        #     f.write(image_bytes)

        # file_key = f"image_generation/{str(uuid.uuid4())}{file_extension}"

        # Upload file to S3
        # s3_client.upload_fileobj(
        #     open(image_path, "rb"),
        #     bucket_name,
        #     file_key,
        #     ExtraArgs={'ACL': 'public-read','ContentType': 'auto'}
        # )
        # Generate URL
        # file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_key}"
        file_url = "https://underdogcrew-ai.s3.ap-south-1.amazonaws.com/image_generation/e27f5f7a-631b-443a-8d86-c3aedd5e7632.jpeg"

        # Log the image generation
        log_data = {
            "art": request.art,
            "feeling": request.feeling,
            "created_at": datetime.now(),
            "image_url": file_url
        }
        
        await db[settings.MONGODB_DB_NAME]["image_generation_logs"].insert_one(log_data)
        os.remove(filepath)
        # os.remove(image_path)
        return ImageGenerationResponse(
            url=file_url,
            message="Image generated successfully"
        )

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An error occurred on line {exc_tb.tb_lineno}: {str(exc_obj)}")
        try:
            os.remove(filepath)
        except:
            pass
        try:
            os.remove(image_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}") 