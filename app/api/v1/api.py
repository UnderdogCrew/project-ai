from fastapi import APIRouter
from app.api.v1.endpoints import agent_environment, rag, data_management, agent, profile, file_upload, agent_app, dashboard, subscription, webhook
from app.api.v1.endpoints.chat import agent_chat

api_router = APIRouter()
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(data_management.router, prefix="/rag/data", tags=["data-management"]) 
api_router.include_router(agent_environment.router, prefix="/environment", tags=["agent-environment"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(agent_chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(profile.router, prefix="/profile", tags=['profile'])
api_router.include_router(file_upload.router, prefix="/upload", tags=['file_upload'])
api_router.include_router(agent_app.router, prefix="/agent/app", tags=["agent-app"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(subscription.router, prefix="/subscription", tags=["subscription"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
