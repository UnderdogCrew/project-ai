from pymongo import MongoClient
from app.core.config import settings
from bson import ObjectId
from datetime import datetime


def get_agent_data(agent_id):
    """
    Fetch agent data from the MongoDB database using the provided agent_id.
    """
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    agent_data = db[settings.MONGODB_COLLECTION_AGENT_STUDIO].find_one({"_id": ObjectId(agent_id)})
    client.close()
    return agent_data


def save_ai_request(request_data):
    """
    Save the AI request data to the MongoDB database.
    
    :param request_data: A dictionary containing the request data to be saved.
    :return: The ID of the saved document.
    """
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    
    # Add a timestamp to the request data
    request_data['created_at'] = datetime.now()
    
    result = db[settings.MONGODB_COLLECTION_AGENT_CHAT].insert_one(request_data)
    client.close()
    
    return str(result.inserted_id)  # Return the ID of the inserted document


def fetch_manage_data(search_query, skip, limit):
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    collection = db[settings.MONGODB_COLLECTION_DATA_MANAGEMENT].find_one(
        {"_id": ObjectId(search_query)}
    )
    client.close()
    return collection  # Returning the query result