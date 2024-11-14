from fastapi import FastAPI
from app.api.v1.endpoints import agent_environment, rag, data_management, whatsapp_msg
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title=settings.PROJECT_NAME)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    allow_origin_regex=None,
    max_age=600,
)

# Include routers
app.include_router(rag.router, prefix=f"{settings.API_V1_STR}/rag", tags=["rag"])
app.include_router(data_management.router, prefix=f"{settings.API_V1_STR}/rag/data", tags=["data-management"])
app.include_router(whatsapp_msg.router, prefix=f"{settings.API_V1_STR}/whatsapp", tags=["whatsapp"])
app.include_router(agent_environment.router, prefix=f"{settings.API_V1_STR}/environment", tags=["agent-environment"])

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection() 