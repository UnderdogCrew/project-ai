from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongodb import get_database
from app.schemas.agent_app import AgentAppCreate, AgentAppUpdate, AgentAppResponse,PaginatedAgentAppResponse, WebhookPayload
from app.core.config import settings
from bson import ObjectId
from typing import Optional, Any, Dict
from app.core.auth_middlerware import decode_jwt_token, GuestTokenResp
from app.api.v1.endpoints.chat.db_helper import fetch_user_details, update_user_credit
from fastapi.responses import JSONResponse


router = APIRouter()

@router.post("/", response_model=AgentAppResponse)
async def create_agent_app(
    app: AgentAppCreate,
    db: AsyncIOMotorClient = Depends(get_database),
    user_data: GuestTokenResp = Depends(decode_jwt_token)
):
    try:
        user_id = user_data['email']
        # Check if the agentId exists in the database
        existing_agent = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT].find_one({"_id": ObjectId(app.agentId)})
        if not existing_agent:
            raise HTTPException(status_code=404, detail="Agent ID does not exist.")
        # Proceed to insert the new agent app
        document = app.model_dump()
        document['user_id'] = user_id
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].insert_one(document)

        # Fetch the user details based on user_id
        user_details_query = {
            "email": user_id
        }
        user_details = fetch_user_details(query=user_details_query)

        if not user_details:
            print(f"User details not found for user_id: {user_id}. Skipping credit update.")
        else:
            # Update the credit in the user table after verifying the user details
            updated_credit = user_details['credit'] - 1
            if updated_credit < 0:
                print("Insufficient credit for the user.")
                updated_credit = 0

            # Construct the update query
            update_user_credit_query = {
                "_id": ObjectId(user_details['_id'])
            }
            update_user_credit_data = {
                "credit": updated_credit
            }

            # Perform the update
            update_user_credit(query=update_user_credit_query, update_data=update_user_credit_data)

            print(f"User credit updated successfully. Updated credit: {updated_credit}")

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
    db: AsyncIOMotorClient = Depends(get_database),
    user_data: GuestTokenResp = Depends(decode_jwt_token)
):
    try:
        # Build the query filters
        user_id = user_data['email']
        query = {
            "user_id": user_id
        }
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
                                    "$eq": ["$email", "$$createdById"]
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
async def patch_agent_app(app: AgentAppUpdate, db: AsyncIOMotorClient = Depends(get_database),
                          user_data: GuestTokenResp = Depends(decode_jwt_token)
                          ):
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
async def delete_agent_app(app_id: str, db: AsyncIOMotorClient = Depends(get_database),
                           user_data: GuestTokenResp = Depends(decode_jwt_token)):
    try:
        result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_AGENT_APP].delete_one({"_id": ObjectId(app_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Agent app not found")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
    

# ---- Your processing function (stub) ----
def process_scraped_page(page: Dict[str, Any]) -> None:
    # TODO: implement your processing logic
    # e.g., save to DB, enqueue a job, etc.
    print(f"Processing page with URL: {page.get('metadata', {}).get('sourceURL')}")


@router.post("/webhook")
async def handle_webhook(payload: WebhookPayload, background: BackgroundTasks) -> JSONResponse:
    success = payload.success
    event_type = payload.type
    job_id = payload.id
    data = payload.data or []
    metadata = payload.metadata or {}
    error = payload.error

    if event_type in ["crawl.started", "batch_scrape.started"]:
        operation = event_type.split(".")[0]
        print(f"{operation} {job_id} started")

    elif event_type in ["crawl.page", "batch_scrape.page"]:
        if success and data:
            page = data[0]
            print(f"Page scraped: {page.get('metadata', {}).get('sourceURL')}")
            # Run processing off the request thread
            background.add_task(process_scraped_page, page)

    elif event_type in ["crawl.completed", "batch_scrape.completed"]:
        operation = event_type.split(".")[0]
        print(f"{operation} {job_id} completed successfully")

    elif event_type in ["crawl.failed", "batch_scrape.failed"]:
        operation = event_type.split(".")[0]
        print(f"{operation} {job_id} failed: {error}")

    return JSONResponse({"status": "received"}, status_code=200)