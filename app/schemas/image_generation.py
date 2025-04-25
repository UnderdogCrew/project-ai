from pydantic import BaseModel
from typing import List, Dict, Optional, Union

class ImageGenerationRequest(BaseModel):
    url: str
    art: Optional[str] = None
    feeling: Optional[str] = None
    transaction_id: str

class ImageGenerationResponse(BaseModel):
    url: str
    message: str