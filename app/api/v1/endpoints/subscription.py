from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.subscription import (
    PlansResponse, SubscriptionCancelRequest,
    SubscriptionResponse,RazorpayOrderRequest
)
from app.utils.razorpay_utils import create_razorpay_subscription, cancel_razorpay_subscription, \
    get_subscription_invoices,create_razorpay_order
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.core.auth_middlerware import JWTBearer
from app.core.config import settings
from datetime import datetime
import calendar

router = APIRouter()



@router.post("/cancel", dependencies=[Depends(JWTBearer())])
async def cancel_subscription(
        cancel_request: SubscriptionCancelRequest,
        request: Request,
        db: AsyncIOMotorClient = Depends(get_database),
):
    try:
        payload = request.state.jwt_payload
        email = payload.get("email")

        subscription = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].find_one({
            "subscription_id": cancel_request.subscription_id,
            "user_email": email
        })

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        razorpay_response, error = cancel_razorpay_subscription(cancel_request.subscription_id)

        if error:
            raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {error}")

        update_result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].update_one(
            {"subscription_id": cancel_request.subscription_id},
            {
                "$set": {
                    "status": "cancelled",
                    "updated_at": datetime.utcnow(),
                    "cancelled_at": datetime.utcnow()
                }
            }
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update subscription status in database")

        return {"message": "Subscription cancelled successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {str(e)}")


@router.post("/create-order", dependencies=[Depends(JWTBearer())])
async def create_order(
        order_request: RazorpayOrderRequest,
        request: Request
):
    try:
        # Extract email from JWT payload
        payload = request.state.jwt_payload
        email = payload.get("email")

        order_data, error = create_razorpay_order(amount=order_request.amount, currency=order_request.currency, receipt=order_request.receipt, 
                                                  notes={"email": email,"credit": order_request.amount/100})
        if error:
            raise HTTPException(status_code=500, detail=f"Failed to create order: {error}")

        return {
            "message": "Order created successfully",
            "order_id": order_data.get("id"),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


@router.get("", dependencies=[Depends(JWTBearer())], response_model=SubscriptionResponse)
async def get_subscription(
        plan_id: str,
        request: Request,
        db: AsyncIOMotorClient = Depends(get_database),
):
    email = request.state.jwt_payload.get("email")
    subscription = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].find_one(
        {"user_email": email}
    )

    if not subscription:
        total_count = 24
        # Create subscription in Razorpay
        razorpay_response, error = create_razorpay_subscription(
            plan_id=plan_id,
            email=email,
            total_count=total_count,
        )

        if error:
            raise HTTPException(status_code=500, detail=f"Failed to create subscription: {error}")

        order_id = ""
        invoices, error = get_subscription_invoices(razorpay_response.get("id"))
        if error:
            print(f"Error fetching invoices: {error}")
        else:
            order_id = invoices["items"][0]["order_id"]

        # Store subscription data in the database with initial status as "pending"
        subscription_data = {
            "user_email": email,
            "subscription_id": razorpay_response.get("id"),
            "plan_id": plan_id,
            "total_count": total_count,
            "status": razorpay_response.get("status"),
            "short_url": razorpay_response.get("short_url"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "order_id": order_id
        }
        await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].insert_one(subscription_data)
        subscription = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].find_one(
            {"user_email": email}
        )
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")


    created_date = subscription["created_at"]
    current_date = datetime.utcnow()

    if subscription["status"] == "cancelled":
        last_day = calendar.monthrange(created_date.year, created_date.month)[1]
        access_end_date = created_date.replace(day=last_day, hour=23, minute=59, second=59)
        subscription["access_valid_till"] = access_end_date
        subscription["has_access"] = current_date <= access_end_date
    elif subscription["status"] == "active":
        subscription["has_access"] = True
        subscription["access_valid_till"] = None
    else:
        subscription["has_access"] = False
        subscription["access_valid_till"] = None

    return SubscriptionResponse(**subscription)



@router.get("/plans", response_model=PlansResponse)
async def get_plans(
        db: AsyncIOMotorClient = Depends(get_database),
):
    try:
        plans = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_PLANS].find().to_list(None)
        if not plans:
            return PlansResponse(plans=[])
        for plan in plans:
            plan["_id"] = str(plan["_id"])
        return PlansResponse(plans=plans)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch plans: {str(e)}")


@router.post("/webhook")
async def razorpay_webhook(
        request: Request,
        db: AsyncIOMotorClient = Depends(get_database)
):
    payload = await request.json()

    # Verify the webhook signature (optional but recommended)
    # You can implement signature verification here if needed
    print(payload)
    event = payload.get("event")
    subscription_id = payload.get("payload", {}).get("subscription", {}).get("entity", {}).get("id",None)

    if event == "subscription.activated":
        if subscription_id:
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].update_one(
                {"subscription_id": subscription_id},
                {"$set": {"status": "active", "updated_at": datetime.utcnow()}}
            )

    elif event == "subscription.deactivated":
        if subscription_id:
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].update_one(
                {"subscription_id": subscription_id},
                {"$set": {"status": "inactive", "updated_at": datetime.utcnow()}}
            )

    elif event == "subscription.pending":
        if subscription_id:
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].update_one(
                {"subscription_id": subscription_id},
                {"$set": {"status": "pending", "updated_at": datetime.utcnow()}}
            )

    elif event == "subscription.charged":
        if subscription_id:
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].update_one(
                {"subscription_id": subscription_id},
                {"$set": {"status": "active", "updated_at": datetime.utcnow()}}
            )

    elif event == "subscription.cancelled":
        if subscription_id:
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].update_one(
                {"subscription_id": subscription_id},
                {"$set": {"status": "cancelled", "updated_at": datetime.utcnow()}}
            )

    elif event == "subscription.completed":
        if subscription_id:
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].update_one(
                {"subscription_id": subscription_id},
                {"$set": {"status": "completed", "updated_at": datetime.utcnow()}}
            )

    elif event == "subscription.expired":
        if subscription_id:
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_SUBSCRIPTIONS].delete_one(
                {"subscription_id": subscription_id}
            )

    elif event == "payment.authorized":
        email = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {}).get("email")
        if email:
            # Assuming the order notes contain the credit amount to be added
            credit_to_add = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {}).get("credit", 0)
            await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_USER].update_one(
                {"email": email},
                {"$inc": {"credit": credit_to_add}}
            )

    return {"status": "success"} 