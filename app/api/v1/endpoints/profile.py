from fastapi import APIRouter, HTTPException, Request, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

from app.core.auth_middlerware import JWTBearer
from app.db.mongodb import get_database
from app.core.config import settings
from app.schemas.user import UserProfile, UserProfileResponse
from app.utils.razorpay_utils import create_razorpay_customer

router = APIRouter()

@router.post("/", dependencies=[Depends(JWTBearer())], response_model=UserProfileResponse)
async def create_profile(
    request: Request,
    db: AsyncIOMotorClient = Depends(get_database)
):
    payload = request.state.jwt_payload

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email not found in token"
        )
    
    # Check if user exists
    existing_user = await db[settings.MONGODB_DB_NAME]["users"].find_one({"email": email,"status":"ACTIVE"})
    if not existing_user:
        # Create new user profile
        user_data = {
            "email": email,
            "name": payload.get('name'),
            "status": "ACTIVE",
            "credit": float(100),
            "profilePic": payload.get("picture") if "picture" in payload else "",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Create Razorpay customer
        razorpay_customer, error = create_razorpay_customer(email, payload.get('contact', ''))
        if error:
            raise HTTPException(status_code=500, 
                                detail=f"Failed to create Razorpay customer: {error}")

        # Add Razorpay customer ID to user data
        user_data["razorpay_customer_id"] = razorpay_customer.get("id")

        await db[settings.MONGODB_DB_NAME]["users"].insert_one(user_data)
        return UserProfileResponse(
            email=email,
            name=payload.get("name"),
            message="Profile created successfully"
        )
    
    return UserProfileResponse(
        email=email,
        name=existing_user.get("name"),
        message="Profile already exists"
    )

@router.get("/{email}",dependencies=[Depends(JWTBearer())], response_model=UserProfile)
async def get_profile(
    email: str,
    db: AsyncIOMotorClient = Depends(get_database)
):
    user = await db[settings.MONGODB_DB_NAME]["users"].find_one({"email": email,"status":"ACTIVE"})
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found or not Active"
        )
    
    return UserProfile(
        email=user["email"],
        name=user.get("name"),
        created_at=user.get("created_at"),
        updated_at=user.get("updated_at")
    )