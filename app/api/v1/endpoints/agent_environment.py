from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.schemas.agent_studio import (
    EnvironmentConfig,
    EnvironmentResponse,
    PaginatedEnvironmentResponse,
    EnvironmentUpdatePayload
)
from app.core.config import settings
from typing import List
from bson import ObjectId

router = APIRouter()


@router.post("/", response_model=EnvironmentResponse)
async def create_environment(
        config: EnvironmentConfig,
        db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        # Create a single document containing both environment and agents
        document = config.model_dump()
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_STUDIO].insert_one(document)

        return EnvironmentResponse(
            id=str(result.inserted_id),
            name=document["name"],
            features=document["features"],
            tools=document["tools"],
            llm_config=document["llm_config"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedEnvironmentResponse)
async def list_environments(
        environment_id: str = None,
        skip: int = 0,
        limit: int = 10,
        search: str = None,
        db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        # Build query filters
        query = {}
        if environment_id:
            query["_id"] = ObjectId(environment_id)
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"environment.description": {"$regex": search, "$options": "i"}}
            ]

        # Get total count
        total = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_STUDIO].count_documents(query)

        # Execute query with pagination
        studios = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_STUDIO].find(query).skip(
            skip).limit(limit).to_list(length=None)

        return PaginatedEnvironmentResponse(
            total=total,
            data=[
                EnvironmentResponse(
                    id=str(studio["_id"]),
                    name=studio["name"],
                    features=studio["features"],
                    tools=studio["tools"],
                    llm_config=studio["llm_config"]
                )
                for studio in studios
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/", response_model=EnvironmentResponse)
async def update_environment(
        payload: EnvironmentUpdatePayload,
        db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        # Build update document based on provided fields
        update_doc = {}
        if payload.model_dump():
            update_doc = payload.model_dump()

        if not update_doc:
            raise HTTPException(status_code=400, detail="No update data provided")

        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_STUDIO].find_one_and_update(
            {"_id": ObjectId(payload.environment_id)},
            {"$set": update_doc},
            return_document=True
        )

        if not result:
            raise HTTPException(status_code=404, detail="Environment not found")

        return EnvironmentResponse(
            id=str(result["_id"]),
            name=result["name"],
            features=result["features"],
            tools=result["tools"],
            llm_config=result["llm_config"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{environment_id}", status_code=204)
async def delete_environment(
        environment_id: str,
        db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_STUDIO].delete_one(
            {"_id": ObjectId(environment_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Environment not found")

        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
