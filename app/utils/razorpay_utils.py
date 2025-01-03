import requests
from app.core.config import settings
from datetime import datetime

def create_razorpay_customer(email: str, contact: str):
    url = "https://api.razorpay.com/v1/customers"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {settings.RAZORPAY_API_KEY}:{settings.RAZORPAY_API_SECRET}"
    }
    
    payload = {
        "name": email.split('@')[0],  # Use email prefix as name
        "email": email,
        "contact": contact
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        return None, response.json()
    
    return response.json(), None 

def create_razorpay_subscription(plan_id: str, customer_id: str, total_count: int, quantity: int = 1, customer_notify: int = 1, start_at: int = None, expire_by: int = None, addons: list = None, gst_percentage: float = 18.0):
    url = "https://api.razorpay.com/v1/subscriptions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {settings.RAZORPAY_API_KEY}:{settings.RAZORPAY_API_SECRET}"
    }
    
    # Calculate GST and total amount
    base_amount = 1000  # Example base amount, replace with your actual logic
    gst_amount = (base_amount * gst_percentage) / 100
    total_amount = base_amount + gst_amount

    # Set the expiry time (current time + expiry_duration in seconds)
    if start_at is None:
        start_at = int(datetime.utcnow().timestamp())
    if expire_by is None:
        expire_by = start_at + 86400  # Default to 1 day later

    # Prepare the payload
    payload = {
        "plan_id": plan_id,
        "total_count": total_count,
        "quantity": quantity,
        "customer_notify": customer_notify,
        "start_at": start_at,
        "expire_by": expire_by,
        "addons": addons or [],
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        return None, response.json()
    
    return response.json(), None