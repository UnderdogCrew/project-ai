from fastapi import APIRouter, Depends, Request
from app.db.mongodb import get_database
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import datetime

router = APIRouter()

@router.post("/razorpay-webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncIOMotorClient = Depends(get_database)
):
    payload = await request.json()
    
    # Verify the webhook signature (optional but recommended)
    # You can implement signature verification here if needed

    event = payload.get("event")
    if event == "subscription.activated":
        subscription_id = payload.get("payload", {}).get("subscription", {}).get("id")
        if subscription_id:
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].update_one(
                {"subscription_id": subscription_id},
                {"$set": {"status": "active", "updated_at": datetime.utcnow()}}
            )
    
    elif event == "subscription.deactivated":
        subscription_id = payload.get("payload", {}).get("subscription", {}).get("id")
        if subscription_id:
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].update_one(
                {"subscription_id": subscription_id},
                {"$set": {"status": "inactive", "updated_at": datetime.utcnow()}}
            )
    
    return {"status": "success"} 