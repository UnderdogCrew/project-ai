from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

from app.db.mongodb import get_database
from fastapi.responses import StreamingResponse, JSONResponse
from app.core.config import settings
from app.core.auth_middlerware import decode_jwt_token, GuestTokenResp

router = APIRouter()



@router.get("/")
async def dashboard_apps(
    db: AsyncIOMotorClient = Depends(get_database),
    user_data: GuestTokenResp = Depends(decode_jwt_token)
):
    try:
        # Build the query filters
        user_id = user_data['email']
        email_query = {
            "email": user_id
        }

        used_credit = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_USER].find_one(email_query)

        remaining_credit = 0
        if used_credit is not None:
            remaining_credit = used_credit['credit']

        agent_counts = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].count_documents({"user_id": user_id})

        chat_counts = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_CHAT].count_documents({"user_id": user_id})


        return JSONResponse(
            status_code=200,
            content={
                "used_credit": remaining_credit,
                "agent_counts": agent_counts,
                "chat_counts": chat_counts
            }
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))