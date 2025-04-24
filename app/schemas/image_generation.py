from pydantic import BaseModel

class ImageGenerationRequest(BaseModel):
    text: str

class ImageGenerationResponse(BaseModel):
    url: str
    message: str