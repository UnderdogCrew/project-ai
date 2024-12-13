from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.schemas.agent_app import AgentAppCreate, AgentAppUpdate, AgentAppResponse,PaginatedAgentAppResponse
from app.core.config import settings
from bson import ObjectId
from typing import List, Optional

router = APIRouter()

@router.post("/", response_model=AgentAppResponse)
async def create_agent_app(
    app: AgentAppCreate,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        # Check if the agentId exists in the database
        existing_agent = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].find_one({"_id": ObjectId(app.agentId)})
        if not existing_agent:
            raise HTTPException(status_code=404, detail="Agent ID does not exist.")
        # Proceed to insert the new agent app
        document = app.model_dump()
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].insert_one(document)
        return AgentAppResponse(id=str(result.inserted_id), **document)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=PaginatedAgentAppResponse)
async def list_agent_apps(
    skip: int = 0,
    limit: int = 10,
    created_by_id: Optional[str] = None, 
    search: Optional[str] = None,
    is_public: Optional[bool] = None,
    app_id: Optional[str] = None,
    db: AsyncIOMotorClient = Depends(get_database)
):
    try:
        # Build the query filters
        query = {}
        if app_id:
            query["_id"] = ObjectId(app_id)

        if search:
            query["appName"] = {"$regex": search, "$options": "i"}  # Case-insensitive search
        
        if is_public:
            query["isPublic"] = True
        
        if created_by_id:
            query["createdById"] = created_by_id  # Use actual user ID logic

        # Fetch total count for pagination
        total = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].count_documents(query)

        if total == 0:
            raise HTTPException(status_code=404, detail="Agent apps not found.")
        # Use aggregation to perform a lookup for user details
        pipeline = [
            {"$match": query},
            {
                "$lookup": {
                    "from": settings.MONGODB_COLLECTION_USER,
                    "let": {"createdById": "$createdById"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$eq": ["$_id", {"$toObjectId": "$$createdById"}]
                                }
                            }
                        }
                    ],
                    "as": "userDetails"
                }
            },
            {
                "$unwind": {
                    "path": "$userDetails",
                    "preserveNullAndEmptyArrays": True  # Keep apps without user details
                }
            },
            {
                "$project": {
                    "id": {"$toString": "$_id"},
                    "agentId": 1,  # Ensure agentId is included
                    "appName": 1,
                    "isPublic": 1,
                    "appIconUrl": 1,
                    "createdById": 1,
                    "createdByName": "$userDetails.name",  # Get the user's name
                    "categories": 1,
                    "description": 1
                }
            },
            {"$skip": skip},
            {"$limit": limit}
        ]
        apps = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].aggregate(pipeline).to_list(length=None)

        return PaginatedAgentAppResponse(
            total=total,
            apps=apps
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/", response_model=AgentAppResponse)
async def patch_agent_app(app: AgentAppUpdate, db: AsyncIOMotorClient = Depends(get_database)):
    try:
        # Ensure app_id is provided in the request body
        if not app.app_id:
            raise HTTPException(status_code=400, detail="app_id is required in the request body.")

        # Prepare the update data, excluding unset fields
        update_data = app.model_dump(exclude_unset=True)
        update_data.pop('app_id', None)
        # Perform the update operation
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].find_one_and_update(
            {"_id": ObjectId(app.app_id)},  # Use agentId to find the document
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