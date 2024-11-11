from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from typing import Optional
import os
from app.core.config import settings

router = APIRouter()

class WhatsAppMessage(BaseModel):
    phone_number: str
    message: str
    template_name: Optional[str] = None

@router.post("/send-message")
async def send_whatsapp_message(message_data: WhatsAppMessage):
    try:
        # WhatsApp Business API configuration
        access_token = settings.WHATSAPP_ACCESS_TOKEN
        phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        version = 'v20.0'  # Meta API version
        
        url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Format the phone number (remove '+' if present)
        to_phone = message_data.phone_number.replace("+", "")
        
        # Prepare the payload
        payload = {
            "messaging_product": "whatsapp",
            "to": "91" + to_phone,
            "type": "template",
            "template": {
                "name": "hello_world",
                "language": {
                    "code": "en_US"
                }
            }
        }

        # If template is provided, use template message instead
        if message_data.template_name:
            payload = {
                "messaging_product": "whatsapp",
                "to": "91" + to_phone,
                "type": "template",
                "template": {
                    "name": "hello_world",
                    "language": {
                        "code": "en"
                    }
                }
            }
        print(payload)
        print(url)
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": "Message sent successfully",
            "details": response.json()
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send WhatsApp message: {str(e)}"
        )
