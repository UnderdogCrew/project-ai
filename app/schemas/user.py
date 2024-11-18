from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class TokenPayload(BaseModel):
    sub: str = None
    exp: int = None
    name: str = None
    email: str = None

class UserProfile(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserProfileResponse(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    message: str

