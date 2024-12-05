from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class GenerateAgentChatSchema (BaseModel):
    session_id: str
    agent_id: str
    user_id: str
    message: Optional[str] = None
    schema: Optional[dict] = None