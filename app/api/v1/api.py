from fastapi import APIRouter
from app.api.v1.endpoints import agent_environment, rag, data_management, agent

api_router = APIRouter()
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(data_management.router, prefix="/rag/data", tags=["data-management"]) 
api_router.include_router(agent_environment.router, prefix="/environment", tags=["agent-environment"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])