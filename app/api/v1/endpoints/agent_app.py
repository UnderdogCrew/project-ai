from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.schemas.agent_app import AgentAppCreate, AgentAppUpdate, AgentAppResponse
from app.core.config import settings
from bson import ObjectId

router = APIRouter()

@router.post("/", response_model=AgentAppResponse)
async def create_agent_app(
    app: AgentAppCreate,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        # Check if the agentId exists in the database
        existing_agent = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].find_one({"agentId": ObjectId(app.agentId)})
        if not existing_agent:
            raise HTTPException(status_code=404, detail="Agent ID does not exist.")
        # Proceed to insert the new agent app
        document = app.model_dump()
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].insert_one(document)
        return AgentAppResponse(id=str(result.inserted_id), **document)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{app_id}", response_model=AgentAppResponse)
async def read_agent_app(app_id: str, db: AsyncIOMotorClient = Depends(get_database)):
    try:
        # Fetch the agent app
        app = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].find_one({"_id": ObjectId(app_id)})
        if app is None:
            raise HTTPException(status_code=404, detail="Agent app not found")

        # Fetch the user details using createdById
        user = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_USER].find_one({"_id": ObjectId(app["createdById"])})
        created_by_name = user["name"] if user else "Unknown"

        # Return the response including the user's name
        return AgentAppResponse(id=str(app["_id"]), **app, createdByName=created_by_name)
    except HTTPException as http_exc:
        raise http_exc  # Re-raise the HTTPException to preserve the status code
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{app_id}", response_model=AgentAppResponse)
async def patch_agent_app(app_id: str, app: AgentAppUpdate, db: AsyncIOMotorClient = Depends(get_database)):
    try:
        # Prepare the update data, excluding unset fields
        update_data = app.model_dump(exclude_unset=True)
        
        # Perform the update operation
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].find_one_and_update(
            {"_id": ObjectId(app_id)},
            {"$set": update_data},
            return_document=True
        )
        # Check if the agent app was found and updated
        if result is None:
            raise HTTPException(status_code=404, detail="Agent app not found")
        # Return the updated agent app response
        return AgentAppResponse(id=str(result["_id"]), **result)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{app_id}", status_code=204)
async def delete_agent_app(app_id: str, db: AsyncIOMotorClient = Depends(get_database)):
    try:
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].delete_one({"_id": ObjectId(app_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Agent app not found")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 