from pydantic import BaseModel

class SubscriptionCreateRequest(BaseModel):
    plan_id: str
    customer_id: str
    total_count: int
    currency: str = "INR"

class SubscriptionCreateResponse(BaseModel):
    id: str
    status: str
    customer_id: str
    plan_id: str 