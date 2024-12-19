from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.schemas.agent_studio import (
    AgentConfig,
    AgentResponse,
    PaginatedAgentResponse,
    AgentUpdatePayload
)
from app.core.config import settings
from typing import List
from bson import ObjectId

router = APIRouter()


@router.post("/", response_model=AgentResponse)
async def create_agent(
        config: AgentConfig,
        db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        # Create a single document for the agent
        document = config.model_dump()
        document['user_id'] = '1'
        agent_id = document['agent_id'] if "agent_id" in document else None

        if agent_id is None:
            agent_name = document["name"]
            agent_slug=agent_name.lower().replace(" ", "-")
            document['slug'] = agent_slug
            result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].insert_one(document)
            return AgentResponse(
                id=str(result.inserted_id),
                name=document["name"],
                environment=document["environment"],
                instructions=document["instructions"],
                system_prompt=document["system_prompt"],
                description=document["description"]
            )
        else:
            # Build update document based on provided fields
            update_doc = document
            if 'agent_id' in update_doc:
                del update_doc["agent_id"]

            if "name" in update_doc:
                agent_name = update_doc["name"]
                agent_slug = agent_name.lower().replace(" ", "-")
                update_doc['slug'] = agent_slug

            if not update_doc:
                raise HTTPException(status_code=400, detail="No update data provided")

            result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].find_one_and_update(
                {"_id": ObjectId(agent_id)},
                {"$set": update_doc},
                return_document=True
            )

            if not result:
                raise HTTPException(status_code=404, detail="Agent not found")
            return AgentResponse(
                id=str(result["_id"]),
                name=result["name"],
                environment=result["environment"],
                slug=result['slug'] if "slug" in result else (result["name"]).lower().replace(" ", "-"),
                instructions=result["instructions"],
                system_prompt=result["system_prompt"],
                description=result["description"]
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedAgentResponse)
async def list_agents(
        agent_id: str = None,
        skip: int = 0,
        limit: int = 10,
        search: str = None,
        db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        # Build query filters
        query = {"user_id": "1"}
        if agent_id:
            query["_id"] = ObjectId(agent_id)
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]

        # Get total count
        total = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].count_documents(query)

        # Execute query with pagination
        agents = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].find(query).skip(skip).limit(
            limit).to_list(length=None)

        return PaginatedAgentResponse(
            total=total,
            data=[
                AgentResponse(
                    id=str(agent["_id"]),
                    name=agent["name"],
                    instructions=agent["instructions"],
                    slug=agent['slug'] if "slug" in agent else (agent["name"]).lower().replace(" ", "-"),
                    environment=agent["environment"],
                    system_prompt=agent["system_prompt"],
                    description=agent["description"]
                )
                for agent in agents
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/", response_model=AgentResponse)
async def update_agent(
        payload: AgentUpdatePayload,
        db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        # Build update document based on provided fields
        update_doc = {}
        if payload.model_dump():
            update_doc = payload.model_dump()

        if not update_doc:
            raise HTTPException(status_code=400, detail="No update data provided")

        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].find_one_and_update(
            {"_id": ObjectId(payload.agent_id)},
            {"$set": update_doc},
            return_document=True
        )

        if not result:
            raise HTTPException(status_code=404, detail="Agent not found")

        return AgentResponse(
            id=str(result["_id"]),
            name=result["name"],
            environment=result["environment"],
            slug=result['slug'] if "slug" in result else (result["name"]).lower().replace(" ", "-"),
            instructions=result["instructions"],
            system_prompt=result["system_prompt"],
            description=result["description"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
        agent_id: str,
        db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].delete_one(
            {"_id": ObjectId(agent_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Agent not found")

        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
