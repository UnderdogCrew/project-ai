from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any

class AgentAppBase(BaseModel):
    agentId: str
    isPublic: bool
    appIconUrl: str
    appName: str
    createdById: str
    categories: List[str]
    description: Optional[str] = None

    @field_validator('categories')
    def check_categories_not_empty(cls, v):
        if not v or any(not category for category in v):
            raise ValueError('Categories must contain at least one non-empty string.')
        return v

class AgentAppCreate(AgentAppBase):
    pass

class AgentAppUpdate(BaseModel):
    app_id: str
    agentId: Optional[str] = None
    isPublic: Optional[bool] = None
    appIconUrl: Optional[str] = None
    appName: Optional[str] = None
    createdById: Optional[str] = None
    categories: Optional[List[str]] = None
    description: Optional[str] = None

class AgentAppResponse(AgentAppBase):
    id: str
    createdByName: Optional[str] = None

    class Config:
        orm_mode = True 

class PaginatedAgentAppResponse(BaseModel):
    total: int
    apps: List[AgentAppResponse] 


class WebhookPayload(BaseModel):
    success: Optional[bool] = None
    type: Optional[str] = None
    id: Optional[str] = None
    data: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None