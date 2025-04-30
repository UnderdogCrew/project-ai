from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
import threading
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.core.config import settings
from datetime import datetime
from openai import OpenAI
from app.schemas.image_generation import ImageGenerationRequest, ImageGenerationResponse, PaymentOrderRequest, PaymentOrderResponse, PaymentVerificationRequest, PaymentVerificationResponse, ImageGenerationRequestV1, ImageUrlResponse, ImageGenerationResponseV1
import requests
import os, sys
from app.core.config import settings
import boto3
from app.utils.razorpay_utils import create_razorpay_order, verify_razorpay_payment, verify_payment_signature
import hmac
import hashlib
import uuid
import base64
from typing import List, Optional
from pydantic import BaseModel
import asyncio



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
        payment_order = await db[settings.MONGODB_DB_NAME]["payment_orders"].find_one({"order_id": request.payment_order_id})
        if payment_order is None:
            raise HTTPException(status_code=400, detail="Payment order not found")
        if payment_order['status'] != "completed" and payment_order['is_used'] != True:
            raise HTTPException(status_code=400, detail="Payment order not completed")

        # Generate image using DALL-E 3
        prompt = """
            Generate a image.
        """

        if request.art is not None:
            if request.art != "":
                prompt = f"Convert Image to {request.art} Style Image"
            
        print(f"prompt: {prompt}")

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


        # if request.feeling is not None:
        #     if request.feeling != "":
        #         prompt += f" with Feeling: {request.feeling}"
        
        response = client.images.edit(
            model="gpt-image-1",
            prompt=prompt,
            image=open(filepath, "rb"),
            size="1024x1536",
            quality="high",
            n=1,
        )
        print(response.usage.input_tokens)

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        cost_per_image = 0.080
        total_cost = cost_per_image*1

        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        # Define local folder to save
        image_path = os.path.join(f"{int(datetime.now().timestamp())}_{image_name}")

        # Save the image to a file
        with open(f"{image_path}", "wb") as f:
            f.write(image_bytes)

        file_key = f"image_generation/{str(uuid.uuid4())}{file_extension}"

        # Upload file to S3
        s3_client.upload_fileobj(
            open(image_path, "rb"),
            bucket_name,
            file_key,
            ExtraArgs={'ACL': 'public-read','ContentType': 'auto'}
        )
        # Generate URL
        file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_key}"
        # file_url = "https://underdogcrew-ai.s3.ap-south-1.amazonaws.com/image_generation/e27f5f7a-631b-443a-8d86-c3aedd5e7632.jpeg"

        # Log the image generation
        log_data = {
            "art": request.art,
            "feeling": request.feeling,
            "created_at": datetime.now(),
            "image_url": file_url,
            "payment_order_id": request.payment_order_id,
            "cost_usd": total_cost,  # Add this line,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
        
        await db[settings.MONGODB_DB_NAME]["image_generation_logs"].insert_one(log_data)
        await db[settings.MONGODB_DB_NAME]["payment_orders"].update_one(
            {"order_id": request.payment_order_id},
            {
                "$set": {"is_used": True}
            }
        )
        os.remove(filepath)
        os.remove(image_path)
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
    



@router.post("/create-payment", response_model=PaymentOrderResponse)
async def create_payment(
    request: PaymentOrderRequest,
    db: AsyncIOMotorClient = Depends(get_database),
):
    """
    Create a payment order for image generation credits
    """
    try:
        # Create notes for the order
        notes = {
            "user_id": request.email if request.email is not None else "",
            "service": "image_generation",
        }

        # Use existing razorpay_utils function
        order_response, error = create_razorpay_order(
            amount=request.amount * 100,  # Convert to paise
            currency="INR",
            receipt=f"receipt_{datetime.now().timestamp()}",
            notes=notes
        )

        if error:
            raise HTTPException(status_code=400, detail=str(error))

        # Store order details in MongoDB
        await db[settings.MONGODB_DB_NAME]["payment_orders"].insert_one({
            "order_id": order_response['id'],
            "user_email": request.email if request.email is not None else "",
            "amount": request.amount,
            "status": "created",
            "created_at": datetime.now()
        })

        return PaymentOrderResponse(
            order_id=order_response['id'],
            amount=order_response['amount'],
            currency=order_response['currency'],
            message="Payment order created successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment order: {str(e)}")


@router.post("/verify-payment", response_model=PaymentVerificationResponse)
async def verify_payment(
    request: PaymentVerificationRequest,
    db: AsyncIOMotorClient = Depends(get_database),
):
    """
    Verify Razorpay payment and add credits
    """
    try:
        # Verify signature
        params_dict = {
            'razorpay_payment_id': request.razorpay_payment_id,
            'razorpay_order_id': request.razorpay_order_id,
            'razorpay_signature': request.razorpay_signature
        }

        if not verify_payment_signature(params_dict):
            return PaymentVerificationResponse(
            success=False,
            message="Payment verification failed"
        )   

        # Get payment details
        payment, error = verify_razorpay_payment(request.razorpay_payment_id, request.razorpay_order_id)
        if error:
            raise HTTPException(status_code=400, detail=str(error))
        
        if payment['status'] != "captured":
            raise HTTPException(status_code=400, detail="Payment not captured")
        
        # Update payment status
        await db[settings.MONGODB_DB_NAME]["payment_orders"].update_one(
            {"order_id": request.razorpay_order_id},
            {
                "$set": {
                    "status": "completed",
                    "payment_id": request.razorpay_payment_id,
                    "completed_at": datetime.now()
                }
            }
        )

        return PaymentVerificationResponse(
            success=True,
            message="Payment verified successfully",
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")
    


async def process_image_generation(request: ImageGenerationRequestV1, db, s3_client, bucket_name, region):
    import sys
    filepath = ""
    image_path = ""
    try:
        payment_order = await db[settings.MONGODB_DB_NAME]["payment_orders"].find_one({"order_id": request.payment_order_id})
        if payment_order is None:
            return
        if payment_order['status'] != "completed" and payment_order['is_used'] != True:
            return

        prompt = "Generate a image."
        if request.art is not None and request.art != "":
            prompt = f"Convert Image to {request.art} Style Image"

        image_url = request.url
        image_name = image_url.split("/")[-1]
        filepath = os.path.join(image_name)
        _, file_extension = os.path.splitext(image_name)

        response = requests.get(image_url)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
        else:
            return

        response = client.images.edit(
            model="gpt-image-1",
            prompt=prompt,
            image=open(filepath, "rb"),
            size="1024x1536",
            quality="high",
            n=1,
        )

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost_per_image = 0.080
        total_cost = cost_per_image * 1

        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        image_path = os.path.join(f"{int(datetime.now().timestamp())}_{image_name}")

        with open(f"{image_path}", "wb") as f:
            f.write(image_bytes)

        file_key = f"image_generation/{str(uuid.uuid4())}{file_extension}"

        s3_client.upload_fileobj(
            open(image_path, "rb"),
            bucket_name,
            file_key,
            ExtraArgs={'ACL': 'public-read', 'ContentType': 'auto'}
        )
        file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_key}"

        log_data = {
            "art": request.art,
            "email": request.email,
            "feeling": request.feeling,
            "created_at": datetime.now(),
            "status": "success",
            "image_url": file_url,
            "payment_order_id": request.payment_order_id,
            "cost_usd": total_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }

        await db[settings.MONGODB_DB_NAME]["image_generation_logs"].insert_one(log_data)
        await db[settings.MONGODB_DB_NAME]["payment_orders"].update_one(
            {"order_id": request.payment_order_id},
            {"$set": {"is_used": True}}
        )
        os.remove(filepath)
        os.remove(image_path)
    except Exception as e:
        try:
            os.remove(filepath)
        except:
            pass
        try:
            os.remove(image_path)
        except:
            pass
        
        log_data = {
            "art": request.art,
            "email": request.email,
            "feeling": request.feeling,
            "created_at": datetime.now(),
            "status": "error",
            "message": f"Background image generation failed: {str(e)}",
            "image_url": "",
            "payment_order_id": request.payment_order_id,
            "cost_usd": 0,
            "input_tokens": 0,
            "output_tokens": 0
        }

        await db[settings.MONGODB_DB_NAME]["image_generation_logs"].insert_one(log_data)

        print(f"Background image generation failed: {str(e)}")



@router.post("/generate", response_model=ImageGenerationResponseV1)
async def generate_ai_image(
    request: ImageGenerationRequestV1,
    db: AsyncIOMotorClient = Depends(get_database),
):
    """
    Start image generation in the background and return immediately.
    """
    # Optionally, you can do some quick validation here
    payment_order = await db[settings.MONGODB_DB_NAME]["payment_orders"].find_one({"order_id": request.payment_order_id})
    if payment_order is None:
        raise HTTPException(status_code=400, detail="Payment order not found")
    if payment_order['status'] != "completed" and payment_order['is_used'] != True:
        raise HTTPException(status_code=400, detail="Payment order not completed")

    # # Start background task
    # asyncio.create_task(process_image_generation(request, db, s3_client, bucket_name, region))

    # Respond immediately
    return ImageGenerationResponseV1(
        message="Image generation started. You will be notified when it is complete."
    ) 



@router.get("/list", response_model=List[ImageUrlResponse])
async def get_images_by_email(
    email: str = Query(..., description="User's email to fetch images for"),
    db: AsyncIOMotorClient = Depends(get_database),
):
    """
    Fetch all image URLs for a given email.
    """
    cursor = db[settings.MONGODB_DB_NAME]["image_generation_logs"].find({"email": email, "status": "success"}).sort("_id", -1)
    images = []
    async for doc in cursor:
        images.append(
            ImageUrlResponse(
                image_url=doc.get("image_url", ""),
                art=doc.get("art"),
                feeling=doc.get("feeling"),
            )
        )
    if len(images) == 0:
        raise HTTPException(status_code=404, detail="No images found for this email")
    return images 