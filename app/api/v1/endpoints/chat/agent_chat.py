from app.api.v1.endpoints.chat.generate_response import generate_rag_response, get_response_by_id
from fastapi import APIRouter, HTTPException
from app.schemas.agent_chat_schema.chat_schema import GenerateAgentChatSchema
import threading
from bson import ObjectId


router = APIRouter()


@router.post("/")
def generate_data(request: GenerateAgentChatSchema):
    # Save the document request to the database
    response_id = str(ObjectId())
    print("Request data saved in database")

    # Start a new thread to generate the response
    threading.Thread(
        target=generate_rag_response,
        args=(request, response_id)
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