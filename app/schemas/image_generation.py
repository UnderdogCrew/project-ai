from pydantic import BaseModel
from typing import List, Dict, Optional, Union

class ImageGenerationRequest(BaseModel):
    url: str
    art: Optional[str] = None
    feeling: Optional[str] = None
    payment_order_id: str
    
class ImageGenerationResponse(BaseModel):
    url: str
    message: str


class PaymentOrderRequest(BaseModel):
    email: Optional[str] = None
    amount: int

class PaymentOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    message: str

class PaymentVerificationRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

class PaymentVerificationResponse(BaseModel):
    success: bool
    message: str