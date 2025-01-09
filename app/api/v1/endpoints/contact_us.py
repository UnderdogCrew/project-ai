import datetime

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.responses import JSONResponse

from app.db.mongodb import get_database
from app.schemas.agent_studio import (
    ContactUslist
)
from app.core.config import settings

router = APIRouter()

@router.post("/")
async def create_contact_us(
        config: ContactUslist,
        db: AsyncIOMotorClient = Depends(get_database),
):
    try:
        # Create a single document for the agent
        email = config.email
        name = config.name
        message = config.message

        await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_CONTACT_US].insert_one(
            {
                "email": email,
                "name": name,
                "message": message,
                "status": 0,
                "created_at": datetime.datetime.now()
            }
        )
        return JSONResponse(
            status_code=201,
            content={
                "message": "Contact us creation done",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
