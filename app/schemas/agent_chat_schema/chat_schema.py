from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class GenerateAgentChatSchema (BaseModel):
    session_id: str
    agent_id: str
    user_id: str
    message: Optional[str] = None
    device_id: Optional[str] = None
    schema: Optional[dict] = None