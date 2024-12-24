from app.api.v1.endpoints.chat.generate_response import generate_rag_response, get_response_by_id, get_user_recent_session_by_user_email, get_chat_by_session_id
from fastapi import APIRouter, HTTPException
from app.schemas.agent_chat_schema.chat_schema import GenerateAgentChatSchema
import threading
from bson import ObjectId
from app.core.auth_middlerware import decode_jwt_token, GuestTokenResp
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


@router.post("/")
def generate_data(request: GenerateAgentChatSchema, user_data: GuestTokenResp = Depends(decode_jwt_token)):
    # Save the document request to the database
    response_id = str(ObjectId())
    user_id = user_data['email']
    print("Request data saved in database")

    # Start a new thread to generate the response
    threading.Thread(
        target=generate_rag_response,
        args=(request, response_id, user_id)
    ).start()

    # Return a response indicating that processing has started
    return {"message": "Request is being processed", "status": "processing", "response_id": response_id}


@router.get("/response")
async def fetch_generated_response(response_id: str):
    """
    Fetch the generated response from MongoDB using the response_id.

    Args:
        response_id (str): The ID of the response to fetch.
        db (Session): The database session.

    Returns:
        dict: The generated response if found, otherwise a not found message.
    """
    response = get_response_by_id(response_id=response_id)  # Fetch response from MongoDB

    if response is None:
        raise HTTPException(status_code=404, detail="Response not found")

    return {"response": response}


@router.get("/history")
async def get_chat_history(
    session_id: str,
    skip: int = 0,
    limit: int = 10,
):
    """
    Fetch chat history for a specific session with pagination.

    Args:
        session_id (str): The session ID to fetch history for (query parameter)
        skip (int): Number of records to skip (for pagination)
        limit (int): Maximum number of records to return

    Returns:
        dict: Paginated chat history with total count and messages
    """
    try:
        response = get_chat_by_session_id(session_id=session_id, skip=skip, limit=limit)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch chat history: {str(e)}"
        )


@router.get("/recent-history")
async def get_recent_chat_history(
    device_id: str,
    skip: int = 0,
    limit: int = 10,
    user_data: GuestTokenResp = Depends(decode_jwt_token)
):
    """
    Fetch recent chat sessions with their first messages as chat names.
    """
    try:
        response = get_user_recent_session_by_user_email(device_id=device_id, skip=skip, limit=limit)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recent chat history: {str(e)}"
        )