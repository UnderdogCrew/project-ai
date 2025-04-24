from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.core.config import settings
from datetime import datetime
from openai import OpenAI
from app.schemas.image_generation import ImageGenerationRequest, ImageGenerationResponse
router = APIRouter()
client = OpenAI(api_key=settings.OPENAI_API_KEY)


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
    try:
        
        # Generate image using DALL-E 3
        response = client.images.generate(
            model="gpt-image-1",
            prompt=request.text,
            size="1024x1024",
            quality="low",
            n=1,
        )
        print(response)
        image_url = response.data[0].url

        # Log the image generation
        log_data = {
            "message": request.text,
            "created_at": datetime.now(),
            "image_url": image_url
        }
        
        await db[settings.MONGODB_DB_NAME]["image_generation_logs"].insert_one(log_data)

        return ImageGenerationResponse(
            url=image_url,
            message="Image generated successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}") 