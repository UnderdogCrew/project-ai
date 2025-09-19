from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.core.config import settings
from datetime import datetime
from openai import OpenAI
from app.core.config import settings
from pymongo import MongoClient
from starlette.responses import JSONResponse
from app.schemas.strands_agents import GenerateAgentChatSchema
from app.api.v1.endpoints.chat.generate_response_strands import generate_rag_response_strands, generate_rag_response_strands_streaming_v2
from fastapi.responses import StreamingResponse
from bson import ObjectId
from app.core.auth_middlerware import decode_jwt_token, GuestTokenResp

sync_db = MongoClient(settings.MONGODB_CLUSTER_URL)  # or your MongoDB URI
# sync_db = client[settings.MONGODB_DB_NAME]



router = APIRouter()
client = OpenAI(api_key=settings.OPENAI_API_KEY)


@router.post("/agent/chat/strands/")
async def generate_data_strands(
        request: Request,
        body: GenerateAgentChatSchema, 
        db: AsyncIOMotorClient = Depends(get_database),
        user_data: GuestTokenResp = Depends(decode_jwt_token)
    ):
    print("Api called for generate the response")
    user_id = user_data['email'] if user_data else None
    print("Request data saved in database")
    response_id = str(ObjectId())

    stream = body.stream
    if stream:
        return StreamingResponse(
            generate_rag_response_strands_streaming_v2(
                request=body,
                db=db,
                response_id=response_id,
                user_id=user_id,
            ), #, user_data=user_data),
            media_type='text/event-stream',
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
            },
        )

    response = await generate_rag_response_strands(request=body, db=db, response_id=response_id, user_id=user_id)
    if response.get('status_code', 200) == 200:
        return response
    elif response.get('status_code') == 404:  # Handle 404 status code
        return JSONResponse(status_code=404, content={"message": response.get("message", "Resource not found")})
    elif response.get('status_code') == 400:  # Handle 400 status code
        return JSONResponse(status_code=400, content={"message": response.get("error", "Bad request")})
    elif response.get('status_code') == 401:  # Handle 401 status code
        return JSONResponse(status_code=401, content={"message": response.get("error", "Unauthorized")})
    elif response.get('status_code') == 402: 
        return JSONResponse(status_code=402, content={"message": response.get("error", "Payment required")})
    elif response.get('status_code') == 408:  # Handle 408 status code
        return JSONResponse(status_code=408, content={"message": response.get("error", "Request timeout")})
    elif response.get('status_code') == 429:  # Handle 429 status code
        return JSONResponse(status_code=429, content={"message": response.get("error", "Too many requests")})
    elif response.get('status_code') == 503:  # Handle 503 status code
        return JSONResponse(status_code=503, content={"message": response.get("error", "Service unavailable")})
    else:
        return JSONResponse(status_code=500, content={"message": response.get('error', 'An unexpected error occurred')})