from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None

db = MongoDB()

async def get_database() -> AsyncIOMotorClient:
    return db.client

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.mongodb_connection_string)

async def close_mongo_connection():
    if db.client:
        db.client.close() 