from fastapi import APIRouter, HTTPException, Depends
from app.schemas.subscription import SubscriptionCreateRequest, SubscriptionCreateResponse
from app.utils.razorpay_utils import create_razorpay_subscription
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.core.auth_middlerware import decode_jwt_token, GuestTokenResp
from app.core.config import settings
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=SubscriptionCreateResponse)
async def create_subscription(
    subscription_request: SubscriptionCreateRequest,
    db: AsyncIOMotorClient = Depends(get_database),
    user_data: GuestTokenResp = Depends(decode_jwt_token)
):
    user_id = user_data['email']
    
    # Create subscription in Razorpay
    razorpay_response, error = create_razorpay_subscription(
        plan_id=subscription_request.plan_id,
        customer_id=subscription_request.customer_id,
        total_count=subscription_request.total_count,
        quantity=1,
        customer_notify=1,
        start_at=int(datetime.utcnow().timestamp()),
        expire_by=int(datetime.utcnow().timestamp()) + 86400,  # 1 day later
        addons=[{
            "item": {
                "name": "Delivery charges",
                "amount": 30000,
                "currency": "INR"
            }
        }],
        notes={
            "notes_key_1": "Tea, Earl Grey, Hot",
            "notes_key_2": "Tea, Earl Grey… decaf."
        }
    )
    
    if error:
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {error}")
    
    # Store subscription data in the database with initial status as "pending"
    subscription_data = {
        "user_id": user_id,
        "subscription_id": razorpay_response.get("id"),
        "plan_id": subscription_request.plan_id,
        "customer_id": subscription_request.customer_id,
        "total_count": subscription_request.total_count,
        "currency": subscription_request.currency,
        "status": razorpay_response.get("status"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].insert_one(subscription_data)
    
    return SubscriptionCreateResponse(**razorpay_response) 