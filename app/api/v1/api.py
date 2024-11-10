from fastapi import APIRouter
from app.api.v1.endpoints import rag, data_management

api_router = APIRouter()
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(data_management.router, prefix="/rag/data", tags=["data-management"]) 