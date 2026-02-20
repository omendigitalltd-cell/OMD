from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from calendar import monthrange

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'hotspot-admin-secret-key-2026')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI(title="WiFi Hotspot Admin API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class AdminCreate(BaseModel):
    email: str
    password: str

class AdminLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CustomerBase(BaseModel):
    name: str
    phone: str
    voucher_code: str
    plan: str  # "3_devices" or "4_devices"
    start_date: str  # ISO format date
    is_active: bool = True

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    voucher_code: Optional[str] = None
    plan: Optional[str] = None
    start_date: Optional[str] = None
    is_active: Optional[bool] = None

class CustomerResponse(CustomerBase):
    id: str
    created_at: str
    monthly_rate: float

class RefundRequest(BaseModel):
    amount: float
    duration_weeks: int  # 1, 2, 3, or 4 weeks
    voucher_start_date: str  # ISO format date when voucher started
    refund_start_date: str  # ISO format date when refund calculation starts

class RefundResponse(BaseModel):
    original_amount: float
    duration_weeks: int
    total_days: int
    voucher_start_date: str
    refund_start_date: str
    days_used: int
    days_remaining: int
    daily_rate: float
    refund_amount: float

class ProRataRequest(BaseModel):
    start_day: int
    month: int
    year: int = 2026
    plan: str  # "3_devices" or "4_devices"

class ProRataResponse(BaseModel):
    start_day: int
    month: int
    month_name: str
    year: int
    plan: str
    monthly_rate: float
    days_in_month: int
    days_used: int
    daily_rate: float
    prorata_amount: float

class WhatsAppConfig(BaseModel):
    phone_number_id: str = ""
    business_account_id: str = ""
    access_token: str = ""
    verify_token: str = ""
    is_configured: bool = False

class ReminderSettings(BaseModel):
    enabled: bool = True
    reminder_day: int = 28  # Day of month to send reminder
    reminder_message: str = "Hi {name}, this is a friendly reminder that your WiFi subscription of R{amount} is due on the last day of this month. Voucher: {voucher_code}"

class ReminderLog(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    customer_phone: str
    message: str
    status: str  # "pending", "sent", "delivered", "failed"
    scheduled_for: str
    sent_at: Optional[str] = None
    error: Optional[str] = None

class DashboardStats(BaseModel):
    total_customers: int
    active_customers: int
    three_device_customers: int
    four_device_customers: int
    estimated_monthly_revenue: float
    pending_reminders: int
    sent_reminders: int

# ==================== HELPERS ====================

PLAN_RATES = {
    "3_devices": 200.0,
    "4_devices": 300.0
}

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def get_monthly_rate(plan: str) -> float:
    return PLAN_RATES.get(plan, 200.0)

def calculate_prorata(start_day: int, month: int, year: int, plan: str) -> dict:
    days_in_month = monthrange(year, month)[1]
    days_used = days_in_month - start_day + 1
    monthly_rate = get_monthly_rate(plan)
    daily_rate = monthly_rate / days_in_month
    prorata_amount = round(daily_rate * days_used, 2)
    
    return {
        "start_day": start_day,
        "month": month,
        "month_name": MONTH_NAMES[month],
        "year": year,
        "plan": plan,
        "monthly_rate": monthly_rate,
        "days_in_month": days_in_month,
        "days_used": days_used,
        "daily_rate": round(daily_rate, 2),
        "prorata_amount": prorata_amount
    }

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(email: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": email,
        "exp": expiration,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register_admin(data: AdminCreate):
    existing = await db.admins.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")
    
    admin_doc = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "password": hash_password(data.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.admins.insert_one(admin_doc)
    
    token = create_token(data.email)
    return TokenResponse(access_token=token)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login_admin(data: AdminLogin):
    admin = await db.admins.find_one({"email": data.email})
    if not admin or not verify_password(data.password, admin["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(data.email)
    return TokenResponse(access_token=token)

@api_router.get("/auth/me")
async def get_current_admin(email: str = Depends(verify_token)):
    admin = await db.admins.find_one({"email": email}, {"_id": 0, "password": 0})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return admin

# ==================== CUSTOMER ROUTES ====================

@api_router.get("/customers", response_model=List[CustomerResponse])
async def get_customers(email: str = Depends(verify_token)):
    customers = await db.customers.find({}, {"_id": 0}).to_list(1000)
    for c in customers:
        c["monthly_rate"] = get_monthly_rate(c.get("plan", "3_devices"))
    return customers

@api_router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str, email: str = Depends(verify_token)):
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer["monthly_rate"] = get_monthly_rate(customer.get("plan", "3_devices"))
    return customer

@api_router.post("/customers", response_model=CustomerResponse)
async def create_customer(data: CustomerCreate, email: str = Depends(verify_token)):
    # Check for duplicate voucher code
    existing = await db.customers.find_one({"voucher_code": data.voucher_code})
    if existing:
        raise HTTPException(status_code=400, detail="Voucher code already exists")
    
    customer_doc = {
        "id": str(uuid.uuid4()),
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.customers.insert_one(customer_doc)
    
    response = {**customer_doc, "monthly_rate": get_monthly_rate(data.plan)}
    if "_id" in response:
        del response["_id"]
    return response

@api_router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(customer_id: str, data: CustomerUpdate, email: str = Depends(verify_token)):
    customer = await db.customers.find_one({"id": customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.customers.update_one({"id": customer_id}, {"$set": update_data})
    
    updated = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    updated["monthly_rate"] = get_monthly_rate(updated.get("plan", "3_devices"))
    return updated

@api_router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str, email: str = Depends(verify_token)):
    result = await db.customers.delete_one({"id": customer_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}

# ==================== PRO-RATA ROUTES ====================

@api_router.post("/prorata/calculate", response_model=ProRataResponse)
async def calculate_prorata_endpoint(data: ProRataRequest, email: str = Depends(verify_token)):
    if data.month < 1 or data.month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    
    days_in_month = monthrange(data.year, data.month)[1]
    if data.start_day < 1 or data.start_day > days_in_month:
        raise HTTPException(status_code=400, detail=f"Start day must be between 1 and {days_in_month}")
    
    if data.plan not in PLAN_RATES:
        raise HTTPException(status_code=400, detail="Plan must be '3_devices' or '4_devices'")
    
    result = calculate_prorata(data.start_day, data.month, data.year, data.plan)
    return result

@api_router.get("/prorata/months-2026")
async def get_2026_months(email: str = Depends(verify_token)):
    """Get all months of 2026 with their days count"""
    months = []
    for month in range(1, 13):
        days = monthrange(2026, month)[1]
        months.append({
            "month": month,
            "name": MONTH_NAMES[month],
            "days": days
        })
    return months

# ==================== REFUND ROUTES ====================

@api_router.post("/refund/calculate", response_model=RefundResponse)
async def calculate_refund(data: RefundRequest, email: str = Depends(verify_token)):
    """Calculate refund based on remaining days of voucher"""
    if data.duration_weeks not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Duration must be 1, 2, 3, or 4 weeks")
    
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    try:
        start_date = datetime.fromisoformat(data.start_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    total_days = data.duration_weeks * 7
    daily_rate = data.amount / total_days
    
    # Calculate days from start_date to today
    today = datetime.now(timezone.utc)
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    
    days_used = (today - start_date).days
    
    # If start date is in the future, no days used yet
    if days_used < 0:
        days_used = 0
    
    # Cap days used at total days
    if days_used > total_days:
        days_used = total_days
    
    days_remaining = total_days - days_used
    refund_amount = round(daily_rate * days_remaining, 2)
    
    return RefundResponse(
        original_amount=data.amount,
        duration_weeks=data.duration_weeks,
        total_days=total_days,
        start_date=data.start_date,
        days_used=days_used,
        days_remaining=days_remaining,
        daily_rate=round(daily_rate, 2),
        refund_amount=refund_amount
    )

# ==================== SETTINGS ROUTES ====================

@api_router.get("/settings/whatsapp")
async def get_whatsapp_config(email: str = Depends(verify_token)):
    config = await db.settings.find_one({"type": "whatsapp"}, {"_id": 0})
    if not config:
        return WhatsAppConfig().model_dump()
    return config

@api_router.put("/settings/whatsapp")
async def update_whatsapp_config(data: WhatsAppConfig, email: str = Depends(verify_token)):
    config_doc = {
        "type": "whatsapp",
        **data.model_dump(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.settings.update_one(
        {"type": "whatsapp"},
        {"$set": config_doc},
        upsert=True
    )
    return {"message": "WhatsApp configuration updated"}

@api_router.get("/settings/reminders")
async def get_reminder_settings(email: str = Depends(verify_token)):
    settings = await db.settings.find_one({"type": "reminders"}, {"_id": 0})
    if not settings:
        return ReminderSettings().model_dump()
    return settings

@api_router.put("/settings/reminders")
async def update_reminder_settings(data: ReminderSettings, email: str = Depends(verify_token)):
    settings_doc = {
        "type": "reminders",
        **data.model_dump(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.settings.update_one(
        {"type": "reminders"},
        {"$set": settings_doc},
        upsert=True
    )
    return {"message": "Reminder settings updated"}

# ==================== REMINDER ROUTES ====================

@api_router.get("/reminders/logs", response_model=List[ReminderLog])
async def get_reminder_logs(email: str = Depends(verify_token)):
    logs = await db.reminder_logs.find({}, {"_id": 0}).sort("scheduled_for", -1).to_list(100)
    return logs

@api_router.post("/reminders/send-test")
async def send_test_reminder(customer_id: str, email: str = Depends(verify_token)):
    """Send a test reminder to a specific customer (simulated)"""
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    settings = await db.settings.find_one({"type": "reminders"}, {"_id": 0})
    reminder_settings = ReminderSettings(**(settings or {}))
    
    message = reminder_settings.reminder_message.format(
        name=customer["name"],
        amount=get_monthly_rate(customer["plan"]),
        voucher_code=customer["voucher_code"]
    )
    
    log_doc = {
        "id": str(uuid.uuid4()),
        "customer_id": customer["id"],
        "customer_name": customer["name"],
        "customer_phone": customer["phone"],
        "message": message,
        "status": "pending",
        "scheduled_for": datetime.now(timezone.utc).isoformat(),
        "sent_at": None,
        "error": None
    }
    
    # Check if WhatsApp is configured
    whatsapp_config = await db.settings.find_one({"type": "whatsapp"}, {"_id": 0})
    
    if whatsapp_config and whatsapp_config.get("is_configured"):
        # TODO: Implement actual WhatsApp sending here
        log_doc["status"] = "sent"
        log_doc["sent_at"] = datetime.now(timezone.utc).isoformat()
    else:
        log_doc["status"] = "pending"
        log_doc["error"] = "WhatsApp not configured - message queued"
    
    await db.reminder_logs.insert_one(log_doc)
    
    return {
        "message": "Test reminder queued",
        "status": log_doc["status"],
        "log_id": log_doc["id"]
    }

@api_router.post("/reminders/schedule-monthly")
async def schedule_monthly_reminders(email: str = Depends(verify_token)):
    """Schedule reminders for all active customers"""
    customers = await db.customers.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    settings = await db.settings.find_one({"type": "reminders"}, {"_id": 0})
    reminder_settings = ReminderSettings(**(settings or {}))
    
    scheduled_count = 0
    for customer in customers:
        message = reminder_settings.reminder_message.format(
            name=customer["name"],
            amount=get_monthly_rate(customer["plan"]),
            voucher_code=customer["voucher_code"]
        )
        
        # Schedule for the reminder day of current month
        now = datetime.now(timezone.utc)
        scheduled_date = now.replace(day=min(reminder_settings.reminder_day, monthrange(now.year, now.month)[1]))
        
        log_doc = {
            "id": str(uuid.uuid4()),
            "customer_id": customer["id"],
            "customer_name": customer["name"],
            "customer_phone": customer["phone"],
            "message": message,
            "status": "pending",
            "scheduled_for": scheduled_date.isoformat(),
            "sent_at": None,
            "error": None
        }
        
        await db.reminder_logs.insert_one(log_doc)
        scheduled_count += 1
    
    return {"message": f"Scheduled {scheduled_count} reminders"}

# ==================== DASHBOARD ROUTES ====================

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(email: str = Depends(verify_token)):
    total_customers = await db.customers.count_documents({})
    active_customers = await db.customers.count_documents({"is_active": True})
    three_device = await db.customers.count_documents({"plan": "3_devices", "is_active": True})
    four_device = await db.customers.count_documents({"plan": "4_devices", "is_active": True})
    
    revenue = (three_device * 200) + (four_device * 300)
    
    pending_reminders = await db.reminder_logs.count_documents({"status": "pending"})
    sent_reminders = await db.reminder_logs.count_documents({"status": "sent"})
    
    return DashboardStats(
        total_customers=total_customers,
        active_customers=active_customers,
        three_device_customers=three_device,
        four_device_customers=four_device,
        estimated_monthly_revenue=revenue,
        pending_reminders=pending_reminders,
        sent_reminders=sent_reminders
    )

@api_router.get("/dashboard/recent-customers")
async def get_recent_customers(email: str = Depends(verify_token)):
    customers = await db.customers.find({}, {"_id": 0}).sort("created_at", -1).to_list(5)
    for c in customers:
        c["monthly_rate"] = get_monthly_rate(c.get("plan", "3_devices"))
    return customers

@api_router.get("/dashboard/recent-reminders")
async def get_recent_reminders(email: str = Depends(verify_token)):
    logs = await db.reminder_logs.find({}, {"_id": 0}).sort("scheduled_for", -1).to_list(5)
    return logs

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "WiFi Hotspot Admin API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router and add middleware
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
