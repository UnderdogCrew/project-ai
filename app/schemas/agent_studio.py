from pydantic import BaseModel
from typing import List, Dict, Optional, Union


class LLMConfig(BaseModel):
    provider: str
    model: str
    config: Dict[str, float]


class EnvironmentConfig(BaseModel):
    name: str
    features: List[dict] = []
    tools: List[dict] = []
    llm_config: LLMConfig


class EnvironmentResponse(BaseModel):
    id: str
    name: str
    features: List[dict] = []
    tools: List[dict] = []
    llm_config: LLMConfig


class PaginatedEnvironmentResponse(BaseModel):
    total: int
    data: List[EnvironmentResponse]


class EnvironmentUpdatePayload(BaseModel):
    environment_id: str
    name: Optional[str] = None
    features: Optional[List[dict]] = None
    tools: Optional[List[dict]] = None
    llm_config: Optional[LLMConfig] = None


class AgentConfig(BaseModel):
    name: str
    environment: str
    instructions: Optional[str] = None
    system_prompt: str
    description: Optional[str] = None
    agent_id: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    environment: str
    instructions: Optional[str] = None
    system_prompt: str
    slug: Optional[str] = None
    description: Optional[str] = None


class PaginatedAgentResponse(BaseModel):
    total: int
    data: List[AgentResponse]


class AgentUpdatePayload(BaseModel):
    agent_id: str
    name: Optional[str] = None
    environment: Optional[str] = None
    instructions: Optional[str] = None
    system_prompt: Optional[str] = None
    description: Optional[str] = None


class AgentWaitlist(BaseModel):
    email: str


class ContactUslist(BaseModel):
    email: str
    name: str
    message: str
