from fastapi import APIRouter, HTTPException, Depends, Path
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from app.schemas.rag.schema import RAGConfigCreate, RAGConfigResponse
from app.core.config import settings
from app.db.mongodb import get_database
from typing import Optional, List
from bson import ObjectId
from pydantic import BaseModel

router = APIRouter()


class PaginatedRAGResponse(BaseModel):
    total: int
    items: List[RAGConfigResponse]


class RAGConfigUpdate(BaseModel):
    rag_id: str
    rag_name: Optional[str] = None
    vector_store: Optional[str] = None
    vector_store_url: Optional[str] = None
    vector_store_api_key: Optional[str] = None
    llm_embedding_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    top_k_similarity: Optional[int] = None

    class Config:
        extra = "forbid"


@router.post("/", response_model=RAGConfigResponse)
async def create_rag_config(
        rag_config: RAGConfigCreate,
        db: AsyncIOMotorClient = Depends(get_database)
):
    """
    Create a new RAG configuration
    """
    # Check if RAG name already exists for this user
    existing_rag = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].find_one({
        "rag_name": rag_config.rag_name,
        "user_id": "1"
    })
    if existing_rag:
        raise HTTPException(
            status_code=400,
            detail=f"RAG configuration with name {rag_config.rag_name} already exists"
        )

    # Prepare the RAG config with additional fields
    rag_dict = rag_config.model_dump()
    rag_dict.update({
        "user_id": "1",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    # Insert the new RAG config
    result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].insert_one(rag_dict)

    # Return the created config
    return RAGConfigResponse(
        id=str(result.inserted_id),
        **{k: v for k, v in rag_dict.items() if k not in ['user_id']}
    )


@router.get("/", response_model=PaginatedRAGResponse)
async def get_rag_configs(
        rag_id: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        db: AsyncIOMotorClient = Depends(get_database)
):
    """
    Get RAG configurations with filtering, search, and pagination
    """
    # Build filter query
    query = {"user_id": "1"}

    if rag_id:
        try:
            query["_id"] = ObjectId(rag_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid RAG ID format")

    if search:
        query["rag_name"] = {"$regex": search, "$options": "i"}

    # Get total count
    total = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].count_documents(query)

    # Get paginated results
    cursor = db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].find(
        query
    ).sort("created_at", -1).skip(skip).limit(limit)

    configs = []
    async for config in cursor:
        config["id"] = str(config.pop("_id"))
        config.pop("user_id", None)
        configs.append(config)

    return PaginatedRAGResponse(
        total=total,
        items=configs
    )


@router.patch("/", response_model=RAGConfigResponse)
async def update_rag_config(
        updates: RAGConfigUpdate,
        db: AsyncIOMotorClient = Depends(get_database)
):
    """
    Update a RAG configuration by ID
    """
    try:
        rag_object_id = ObjectId(updates.rag_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid RAG ID format")

    # Check if RAG exists and belongs to user
    existing_rag = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].find_one({
        "_id": rag_object_id,
        "user_id": "1"
    })

    if not existing_rag:
        raise HTTPException(status_code=404, detail="RAG configuration not found")

    # If rag_name is being updated, check for duplicates
    if updates.rag_name and updates.rag_name != existing_rag["rag_name"]:
        name_exists = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].find_one({
            "rag_name": updates.rag_name,
            "user_id": "1",
            "_id": {"$ne": rag_object_id}  # Exclude current document
        })
        if name_exists:
            raise HTTPException(
                status_code=400,
                detail=f"RAG configuration with name {updates.rag_name} already exists"
            )

    # Prepare update dict excluding None values
    update_data = {
        k: v for k, v in updates.model_dump(exclude_unset=True).items()
        if v is not None and k != 'rag_id'  # Exclude rag_id and None values
    }

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    # Update the document
    result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].update_one(
        {"_id": rag_object_id},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Update failed")

    # Get and return the updated document
    updated_rag = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].find_one(
        {"_id": rag_object_id}
    )

    updated_rag["id"] = str(updated_rag.pop("_id"))
    updated_rag.pop("user_id", None)

    return updated_rag


@router.delete("/{rag_id}", response_model=dict)
async def delete_rag_config(
        rag_id: str = Path(..., description="The ID of the RAG config to delete"),
        db: AsyncIOMotorClient = Depends(get_database)
):
    """
    Delete a RAG configuration by ID
    """
    try:
        rag_object_id = ObjectId(rag_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid RAG ID format")

    # Check if RAG exists and belongs to user
    existing_rag = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].find_one({
        "_id": rag_object_id,
        "user_id": "1"
    })

    if not existing_rag:
        raise HTTPException(status_code=404, detail="RAG configuration not found")

    # Delete the document
    result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].delete_one({
        "_id": rag_object_id,
        "user_id": "1"
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=400, detail="Delete failed")

    return {"message": "RAG configuration deleted successfully"}
