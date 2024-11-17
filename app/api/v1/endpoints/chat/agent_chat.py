from fastapi.responses import JSONResponse
from app.api.v1.endpoints.chat.generate_response import generate_rag_response
from datetime import datetime
from fastapi import APIRouter
from app.schemas.agent_chat_schema.chat_schema import GenerateAgentChatSchema
from app.api.v1.endpoints.chat.db_helper import save_ai_request
import queue


router = APIRouter()


@router.post("/")
def generate_data(request: GenerateAgentChatSchema):
    # Save the document request to the database
    data = {
        "message": request.message,
        "user_id": request.user_id,
        "session_id": request.session_id,
        "agent_id": request.agent_id,
        "created_at": datetime.now()
    }
    _ = save_ai_request(request_data=data)
    print("Request data saved in database")

    # Generate the response from the AI
    response = generate_rag_response(request=request)

    # Check the status code of the response
    if response.get('status_code', 200) == 200:
        return response
    else:
        return JSONResponse(status_code=500, content={"message": response.get('text', 'An error occurred')})