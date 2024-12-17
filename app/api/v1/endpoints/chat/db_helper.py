from pymongo import MongoClient
from app.core.config import settings
from bson import ObjectId
from datetime import datetime


def get_agent_data(agent_id):
    """
    Fetch agent data from the MongoDB database using the provided agent_id.
    """
    client = MongoClient(settings.MONGODB_CLUSTER_URL)
    db = client[settings.MONGODB_DB_NAME]
    agent_data = db[settings.MONGODB_COLLECTION_AGENT].find_one({"_id": ObjectId(agent_id)})
    client.close()
    return agent_data


def get_environment_data(env_id):
    """
    Fetch environment data from the MongoDB database using the provided agent_id.
    """
    client = MongoClient(settings.MONGODB_CLUSTER_URL)
    db = client[settings.MONGODB_DB_NAME]
    env_data = db[settings.MONGODB_COLLECTION_AGENT_STUDIO].find_one({"_id": ObjectId(env_id)})
    client.close()
    return env_data


def save_ai_request(request_data):
    """
    Save the AI request data to the MongoDB database.
    
    :param request_data: A dictionary containing the request data to be saved.
    :return: The ID of the saved document.
    """
    client = MongoClient(settings.MONGODB_CLUSTER_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Add a timestamp to the request data
    request_data['created_at'] = datetime.now()

    result = db[settings.MONGODB_COLLECTION_AGENT_CHAT].insert_one(request_data)
    client.close()

    return str(result.inserted_id)  # Return the ID of the inserted document


def fetch_ai_requests_data(query):
    client = MongoClient(settings.MONGODB_CLUSTER_URL)
    db = client[settings.MONGODB_DB_NAME]
    document = db[settings.MONGODB_COLLECTION_AGENT_CHAT].find_one(query)
    return document


def fetch_manage_data(search_query, skip, limit):
    client = MongoClient(settings.MONGODB_CLUSTER_URL)
    db = client[settings.MONGODB_DB_NAME]
    collection = db[settings.MONGODB_COLLECTION_DATA_MANAGEMENT].find_one(search_query, skip=skip, limit=limit)
    client.close()
    return collection  # Returning the query result


def save_website_scrapper_logs(data):
    client = MongoClient(settings.MONGODB_CLUSTER_URL)
    db = client[settings.MONGODB_DB_NAME]

    result = db[settings.MONGODB_COLLECTION_RAG_LOGS].insert_one(data)
    client.close()

    return str(result.inserted_id)  # Return the ID of the inserted document


def update_website_scrapper_logs(data):
    client = MongoClient(settings.MONGODB_CLUSTER_URL)
    db = client[settings.MONGODB_DB_NAME]

    result = db[settings.MONGODB_COLLECTION_RAG_LOGS].update_one(
        {
            "rag_id": data['rag_id'],
            "link": data['link']
        },
        {
            "$set": {
                "page_content": data['page_content'],
                "status": data['status']
            }
        }
    )
    client.close()

    return str(result.modified_count)  # Return the ID of the inserted document


def get_agent_history_data(query, skip, limit):
    client = MongoClient(settings.MONGODB_CLUSTER_URL)
    db = client[settings.MONGODB_DB_NAME]
    agent_data = db[settings.MONGODB_COLLECTION_AGENT_CHAT].find(query).skip(skip).limit(limit).sort("_id", -1)
    return agent_data