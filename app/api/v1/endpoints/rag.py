from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List
from app.models.rag.models import RAGConfig
from app.core.config import settings
from app.db.mongodb import get_database

router = APIRouter()

@router.post("/", response_model=RAGConfig)
async def create_rag_config(
    rag_config: RAGConfig,
    db: AsyncIOMotorClient = Depends(get_database)
):
    """
    Create a new RAG configuration
    """
    # Check if RAG name already exists
    existing_rag = await db[settings.MONGODB_DB_NAME]["rag_configs"].find_one(
        {"rag_name": rag_config.name}
    )
    if existing_rag:
        raise HTTPException(
            status_code=400,
            detail=f"RAG configuration with name {rag_config.name} already exists"
        )

    # Insert the new RAG config
    rag_dict = rag_config.model_dump()
    result = await db[settings.MONGODB_DB_NAME]["rag_configs"].insert_one(rag_dict)
    
    # Return the created config
    return rag_config 