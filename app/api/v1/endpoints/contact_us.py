import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.responses import JSONResponse

from app.db.mongodb import get_database
from app.schemas.agent_studio import (
    ContactUslist
)
from app.core.config import settings
from app.services.email_service import email_service

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
        company = config.company
        message = config.message

        await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_CONTACT_US].insert_one(
            {
                "email": email,
                "name": name,
                "company": company,
                "message": message,
                "status": 0,
                "created_at": datetime.datetime.now()
            }
        )
        
        # Send email to the admin
        try:
            email_sent = await email_service.send_contact_form_to_admin(
                name=name,
                email=email,
                company=company,
                message=message
            )
            
            if email_sent:
                logging.info(f"Contact form email sent successfully to admin for {email}")
            else:
                logging.warning(f"Failed to send contact form email to admin for {email}")
                
        except Exception as e:
            logging.error(f"Error sending contact form email: {str(e)}")
            # Continue execution - don't fail the API call if email fails
        
        return JSONResponse(
            status_code=201,
            content={
                "message": "Contact us creation done",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
