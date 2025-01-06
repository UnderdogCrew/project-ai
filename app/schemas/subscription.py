from pydantic import BaseModel
from typing import List ,Optional
from datetime import datetime

class SubscriptionCreateRequest(BaseModel):
    plan_id: str

class SubscriptionCreateResponse(BaseModel):
    id: str
    status: str
    plan_id: str 
    short_url: str
    
class Plan(BaseModel):
    planid: str
    planname: str
    billing_amount: str

class PlansResponse(BaseModel):
    plans: List[Plan]

class SubscriptionCancelRequest(BaseModel):
    subscription_id: str

class SubscriptionResponse(BaseModel):
    subscription_id: str
    plan_id: str
    status: str
    short_url: str
    total_count: int
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime] = None
    access_valid_till: Optional[datetime] = None
    has_access: bool

