from fastapi import APIRouter, Depends, HTTPException, Path, Query
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.data_management import (
    CreateManageDataSchema,
    ManageDataResponse,
    UpdateManageDataSchema,
    ManageDataListResponse,
    DataSourceType,
    DataStatus
)
import uuid
from app.manage_data.read_file_content import file_data
from app.manage_data.website_scrapper import scrap_website
from qdrant_client.http.models import PointStruct, VectorParams
from qdrant_client import QdrantClient
from uuid import uuid4
import sys
from app.core.config import settings
import os
from app.core.auth_middlerware import decode_jwt_token, GuestTokenResp

os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
from openai import OpenAI

client = OpenAI()

QDRANT_URL = settings.QDRANT_API_URL
QDRANT_API_KEY = settings.QDRANT_API_KEY

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=300
)

import threading
from typing import Optional, Union


def process_data_source(
        source_type: DataSourceType,
        rag_object_id: ObjectId,
        files: Optional[List[str]] = None,
        website_url: Optional[str] = None,
        raw_text: Optional[str] = None,
        max_crawl_depth: Optional[int] = 1,
        max_crawl_page: Optional[int] = 1,
        dynamic_wait: Optional[int] = 5
) -> None:
    """Process different types of data sources in a separate thread"""
    if source_type == DataSourceType.FILE and files:
        for _file in files:
            file_data(url=_file, rag_manage_id=rag_object_id)

    elif source_type == DataSourceType.WEBSITE and website_url:
        scrap_website(rag_object_id, website_url, "1", max_crawl_depth, max_crawl_page, dynamic_wait)

    elif source_type == DataSourceType.RAW_TEXT and raw_text:
        embedding_id = f"{str(rag_object_id)}"

        if not qdrant_client.collection_exists(embedding_id):
            qdrant_client.create_collection(
                collection_name=embedding_id,
                vectors_config=VectorParams(size=1536, distance='Cosine')
            )

        try:
            if raw_text:
                metadata = {'title': raw_text}
                points = []
                resp = _create_embeddings(raw_text)
                p_uuid = str(uuid.uuid4())
                points.append(
                    PointStruct(id=p_uuid, vector=resp.embedding,
                                payload={"metadata": metadata, "page_content": raw_text})
                )
                qdrant_client.upsert(
                    collection_name=embedding_id,
                    points=points
                )
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(f"An error occurred on line {exc_tb.tb_lineno}: {str(exc_obj)}")
            raise Exception("Error processing raw text")

    return True


def _create_embeddings(input: str):
    results = client.embeddings.create(
        input=[input],
        model="text-embedding-ada-002"
    )
    content = results.data[0]
    return content


router = APIRouter()


@router.post("/", response_model=ManageDataResponse)
async def create_data_management(
        data: CreateManageDataSchema,
        db: AsyncIOMotorClient = Depends(get_database),
        user_data: GuestTokenResp = Depends(decode_jwt_token)
):
    """Create a new data management request"""
    # Validate RAG ID
    user_id = user_data['email']
    try:
        rag_object_id = ObjectId(data.rag_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid RAG ID format")

    # Check if RAG exists and belongs to user
    existing_rag = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_RAG_CONFIGS].find_one({
        "_id": rag_object_id,
        "user_id": user_id
    })

    if not existing_rag:
        raise HTTPException(status_code=404, detail="RAG configuration not found")

    # Determine source type
    source_type = None
    if data.files:
        source_type = DataSourceType.FILE
    elif data.website_url:
        source_type = DataSourceType.WEBSITE
    elif data.raw_text:
        source_type = DataSourceType.RAW_TEXT
    else:
        raise HTTPException(status_code=400, detail="No data source provided")

    # Start processing in a separate thread
    process_thread = threading.Thread(
        target=process_data_source,
        args=(source_type, rag_object_id),
        kwargs={
            'files': data.files,
            'website_url': data.website_url,
            'raw_text': data.raw_text,
            "max_crawl_depth": data.max_crawl_depth,
            "max_crawl_page": data.max_crawl_page,
            "dynamic_wait": data.dynamic_wait
        }
    )
    process_thread.start()

    # Create document
    new_data = {
        **data.model_dump(exclude_none=True),
        "source_type": source_type,
        "status": DataStatus.COMPLETED,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "user_id": user_id
    }

    result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].insert_one(new_data)

    # Get and return the created document
    created_data = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].find_one(
        {"_id": result.inserted_id}
    )
    created_data["id"] = str(created_data.pop("_id"))
    created_data.pop("user_id", None)

    return created_data


@router.get("/", response_model=ManageDataListResponse)
async def list_data_management(
        rag_id: Optional[str] = None,
        status: Optional[DataStatus] = None,
        skip: int = Query(default=0, ge=0),
        limit: int = Query(default=10, ge=1, le=100),
        db: AsyncIOMotorClient = Depends(get_database),
        user_data: GuestTokenResp = Depends(decode_jwt_token)
):
    user_id = user_data['email']
    """List all data management requests"""
    query = {"user_id": user_id}

    if rag_id:
        try:
            query["rag_id"] = str(ObjectId(rag_id))
        except:
            raise HTTPException(status_code=400, detail="Invalid RAG ID format")

    if status:
        query["status"] = status

    # Get total count
    total = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].count_documents(query)

    # Get items with pagination
    cursor = db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].find(query)
    cursor.skip(skip).limit(limit).sort("created_at", -1)

    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        doc.pop("user_id", None)
        items.append(doc)

    # Validate if items list is empty
    if not items:
        raise HTTPException(status_code=404, detail="No data management requests found")

    return {
        "total": total,
        "items": items
    }


@router.get("/{data_id}", response_model=ManageDataResponse)
async def get_data_management(
        data_id: str = Path(..., description="The ID of the data management request"),
        db: AsyncIOMotorClient = Depends(get_database),
        user_data: GuestTokenResp = Depends(decode_jwt_token)
):
    """Get a specific data management request"""
    user_id = user_data['email']
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid data ID format")

    data = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].find_one({
        "_id": data_object_id,
        "user_id": user_id
    })

    if not data:
        raise HTTPException(status_code=404, detail="Data management request not found")

    data["id"] = str(data.pop("_id"))
    data.pop("user_id", None)

    return data


@router.delete("/{data_id}", response_model=dict)
async def delete_data_management(
        data_id: str = Path(..., description="The ID of the data management request to delete"),
        db: AsyncIOMotorClient = Depends(get_database),
        user_data: GuestTokenResp = Depends(decode_jwt_token)
):
    """Delete a data management request"""
    user_id = user_data['email']
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid data ID format")

    # Check if data exists and belongs to user
    existing_data = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].find_one({
        "_id": data_object_id,
        "user_id": user_id
    })

    if not existing_data:
        raise HTTPException(status_code=404, detail="Data management request not found")

    # Delete the document
    result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].delete_one({
        "_id": data_object_id,
        "user_id": "1"
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=400, detail="Delete failed")

    return {"message": "Data management request deleted successfully"}


@router.patch("/", response_model=ManageDataResponse)
async def update_data_management(
        data: UpdateManageDataSchema,
        db: AsyncIOMotorClient = Depends(get_database)
):
    """Update an existing data management request"""
    if not data.data_id:
        raise HTTPException(status_code=400, detail="data_id is required")

    try:
        data_object_id = ObjectId(data.data_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid data ID format")

    # Check if data exists and belongs to user
    existing_data = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].find_one({
        "_id": data_object_id,
        "user_id": "1"
    })

    if not existing_data:
        raise HTTPException(status_code=404, detail="Data management request not found")

    # Validate RAG ID
    try:
        rag_object_id = ObjectId(data.rag_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid RAG ID format")

    # Determine source type
    source_type = None
    if data.files:
        source_type = DataSourceType.FILE
    elif data.website_url:
        source_type = DataSourceType.WEBSITE
    elif data.raw_text:
        source_type = DataSourceType.RAW_TEXT
    else:
        raise HTTPException(status_code=400, detail="No data source provided")

    # Start processing in a separate thread
    process_thread = threading.Thread(
        target=process_data_source,
        args=(source_type, rag_object_id),
        kwargs={
            'files': data.files,
            'website_url': data.website_url,
            'raw_text': data.raw_text,
            "max_crawl_depth": data.max_crawl_depth,
            "max_crawl_page": data.max_crawl_page,
            "dynamic_wait": data.dynamic_wait
        }
    )
    process_thread.start()

    # Update document
    update_data = {
        **data.model_dump(exclude_none=True),
        "updated_at": datetime.now()
    }

    result = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].update_one(
        {"_id": data_object_id},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Update failed")

    # Get and return the updated document
    updated_data = await db[settings.MONGODB_DB_NAME][settings.MONGODB_COLLECTION_DATA_MANAGEMENT].find_one(
        {"_id": data_object_id}
    )
    updated_data["id"] = str(updated_data.pop("_id"))
    updated_data.pop("user_id", None)

    return updated_data
