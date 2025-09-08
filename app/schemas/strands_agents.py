from pydantic import BaseModel
from typing import Optional


class GenerateAgentChatSchema(BaseModel):
    session_id: str
    agent_id: str
    message: Optional[str] = None
    stream: Optional[bool] = False