from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form
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
import base64
import re
import pdfplumber
import io
import pytesseract
from PIL import Image

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

# ==================== DISTRIBUTOR MODELS ====================

class DistributorCreate(BaseModel):
    name: str
    email: str
    phone: str
    password: str

class DistributorLogin(BaseModel):
    email: str
    password: str

class DistributorUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class DistributorResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    is_active: bool
    total_sales: float
    total_commission: float
    pending_commission: float
    created_at: str

class ProofOfPaymentCreate(BaseModel):
    reference: str
    amount: float
    customer_phone: Optional[str] = None
    notes: Optional[str] = None

class ProofOfPaymentResponse(BaseModel):
    id: str
    distributor_id: str
    distributor_name: str
    reference: str
    amount: float
    customer_phone: Optional[str]
    notes: Optional[str]
    file_type: str
    status: str  # "pending", "matched", "paid", "rejected"
    matched_at: Optional[str]
    created_at: str

class BankStatementEntry(BaseModel):
    reference: str
    amount: float
    date: str
    description: str

class CommissionSummary(BaseModel):
    distributor_id: str
    distributor_name: str
    total_matched_sales: float
    commission_rate: float
    total_commission: float
    paid_commission: float
    pending_commission: float
    matched_proofs: int
    pending_proofs: int

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

def create_distributor_token(email: str, distributor_id: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": email,
        "distributor_id": distributor_id,
        "role": "distributor",
        "exp": expiration,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def verify_distributor_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "distributor":
            raise HTTPException(status_code=401, detail="Invalid distributor token")
        return {
            "email": payload.get("sub"),
            "distributor_id": payload.get("distributor_id")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def parse_bank_statement_pdf(pdf_content: bytes) -> List[dict]:
    """Parse bank statement PDF and extract transactions"""
    entries = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                
                # Try to extract tables
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and len(row) >= 2:
                            row_text = " ".join([str(cell) for cell in row if cell])
                            # Skip header rows and empty rows
                            if any(header in row_text.lower() for header in ['date', 'description', 'balance', 'transaction']):
                                continue
                            
                            # Look for transaction patterns with amounts
                            # Capitec format: Date | Description | Amount | Balance
                            # Look for R amount or just amount with +/- sign
                            amount_match = re.search(r'[+\-]?\s*[Rr]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2}))', row_text)
                            if amount_match:
                                try:
                                    amount = float(amount_match.group(1).replace(',', ''))
                                    if amount > 0 and amount < 50000:
                                        # Extract reference/name from description
                                        # Look for names in the format: "Transfer M HLONGWANE" or "Deposit SURNAME"
                                        ref_patterns = [
                                            r'(?:Transfer|Deposit|Credit|Payment)\s+([A-Z][A-Z\s]{2,25}?)(?:\s+[+\-R]|\s*$)',
                                            r'(?:from|FROM)\s+([A-Z][A-Z\s]{2,25}?)(?:\s+[+\-R]|\s*$)',
                                            r'\b([A-Z]{2}[A-Z]+)\b',  # Uppercase names
                                        ]
                                        
                                        ref_value = None
                                        for pattern in ref_patterns:
                                            ref_match = re.search(pattern, row_text, re.IGNORECASE)
                                            if ref_match:
                                                ref_value = ref_match.group(1).strip().upper()
                                                # Filter out common non-reference words
                                                if ref_value not in ['CAPITEC', 'BANK', 'BUSINESS', 'ACCOUNT', 'TRANSFER', 'DEPOSIT', 'LOCAL', 'PURCHASE', 'DEBIT', 'ORDER', 'CREDIT']:
                                                    break
                                                ref_value = None
                                        
                                        if ref_value:
                                            entries.append({
                                                "reference": ref_value,
                                                "amount": amount,
                                                "description": row_text[:150],
                                                "date": datetime.now(timezone.utc).isoformat()
                                            })
                                except ValueError:
                                    pass
            
            # Also parse line by line for Capitec statement format
            lines = full_text.split('\n')
            for line in lines:
                # Look for lines with amounts like +60.00 or R60.00
                amount_match = re.search(r'[+]\s*(\d{1,3}(?:,\d{3})*\.\d{2})', line)
                if amount_match:
                    try:
                        amount = float(amount_match.group(1).replace(',', ''))
                        if amount >= 10 and amount < 50000:  # Reasonable payment range
                            # Extract the name/reference from the line
                            # Pattern: "Ret Cr Transfer S BUTHELEZI +60.00"
                            name_match = re.search(r'(?:Transfer|Deposit|Credit)\s+([A-Z](?:\s+)?[A-Z]+)', line, re.IGNORECASE)
                            if name_match:
                                ref_value = name_match.group(1).strip().upper().replace(' ', '_')
                                # Avoid duplicates
                                if not any(e['reference'] == ref_value and abs(e['amount'] - amount) < 0.01 for e in entries):
                                    entries.append({
                                        "reference": ref_value,
                                        "amount": amount,
                                        "description": line[:150],
                                        "date": datetime.now(timezone.utc).isoformat()
                                    })
                    except ValueError:
                        pass
                        
    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
    
    return entries

COMMISSION_RATE = 0.20  # 20% commission

def extract_from_proof_image(image_content: bytes) -> dict:
    """Extract reference and amount from proof of payment image using OCR"""
    try:
        image = Image.open(io.BytesIO(image_content))
        text = pytesseract.image_to_string(image)
        return extract_reference_and_amount(text)
    except Exception as e:
        logger.error(f"Error extracting from image: {str(e)}")
        return {"reference": None, "amount": None, "raw_text": ""}

def extract_from_proof_pdf(pdf_content: bytes) -> dict:
    """Extract reference and amount from proof of payment PDF"""
    try:
        full_text = ""
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        return extract_reference_and_amount(full_text)
    except Exception as e:
        logger.error(f"Error extracting from PDF: {str(e)}")
        return {"reference": None, "amount": None, "raw_text": ""}

def extract_reference_and_amount(text: str) -> dict:
    """Extract reference number and amount from text"""
    result = {"reference": None, "amount": None, "raw_text": text[:500]}
    
    # Normalize text - handle line breaks and multiple spaces
    normalized_text = re.sub(r'\s+', ' ', text)
    
    # Split into lines for line-by-line analysis
    lines = text.split('\n')
    
    # Look for reference on a line that starts with or contains "Reference"
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # Check if line starts with "Reference" and has more content
        if re.match(r'^[Rr]eference\s+', line_stripped):
            # Extract everything after "Reference"
            ref_match = re.search(r'^[Rr]eference\s+(.+)$', line_stripped)
            if ref_match:
                ref_value = ref_match.group(1).strip()
                # Clean up the reference value
                if ref_value and len(ref_value) >= 2 and ref_value.upper() not in ['NUMBER', 'NO', 'N/A', 'NONE']:
                    result["reference"] = ref_value.upper().replace(' ', '_')
                    break
        # Also check for "Reference:" format
        elif 'reference' in line_stripped.lower():
            ref_match = re.search(r'[Rr]eference[:\s]+(.+?)(?:\s{2,}|$)', line_stripped)
            if ref_match:
                ref_value = ref_match.group(1).strip()
                if ref_value and len(ref_value) >= 2 and ref_value.upper() not in ['NUMBER', 'NO', 'N/A', 'NONE']:
                    result["reference"] = ref_value.upper().replace(' ', '_')
                    break
    
    # Fallback patterns if line-by-line didn't work
    if not result["reference"]:
        ref_patterns = [
            r'[Rr]eference\s*[:#]?\s*([A-Za-z0-9\s\-_]{3,30}?)(?:\s{2,}|\n|$)',
            r'[Rr]ef\s*[:#]?\s*([A-Za-z0-9\s\-_]{3,30}?)(?:\s{2,}|\n|$)',
            r'[Pp]ayment\s+[Rr]ef(?:erence)?\s*[:#]?\s*([A-Za-z0-9\s\-_]{3,30}?)(?:\s{2,}|\n|$)',
            r'[Yy]our\s+[Rr]ef(?:erence)?\s*[:#]?\s*([A-Za-z0-9\s\-_]{3,30}?)(?:\s{2,}|\n|$)',
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, text)
            if match:
                ref_value = match.group(1).strip()
                if ref_value and len(ref_value) >= 2 and ref_value.upper() not in ['NUMBER', 'NO', 'N/A', 'NONE', 'THE', 'FOR']:
                    result["reference"] = ref_value.upper().replace(' ', '_')
                    break
    
    # Look for amount patterns - South African Rand
    amount_patterns = [
        r'[Aa]mount\s+[Rr](\d{1,3}(?:[,\s]?\d{3})*(?:[.,]\d{2})?)',  # Amount R60.00
        r'[Aa]mount[:\s]*[Rr]?\s*(\d{1,3}(?:[,\s]?\d{3})*(?:[.,]\d{2})?)',  # Amount: R60.00
        r'[Tt]otal[:\s]*[Rr]?\s*(\d{1,3}(?:[,\s]?\d{3})*(?:[.,]\d{2})?)',   # Total: R60.00
        r'[Pp]aid[:\s]*[Rr]?\s*(\d{1,3}(?:[,\s]?\d{3})*(?:[.,]\d{2})?)',    # Paid: R60.00
        r'[Rr]\s*(\d{1,3}(?:[,\s]?\d{3})*[.,]\d{2})',  # R60.00 (with decimals required)
        r'ZAR\s*(\d{1,3}(?:[,\s]?\d{3})*(?:[.,]\d{2})?)',   # ZAR 60.00
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, normalized_text)
        if match:
            try:
                amount_str = match.group(1).replace(',', '').replace(' ', '')
                # Handle both . and , as decimal separator
                if ',' in amount_str and '.' not in amount_str:
                    amount_str = amount_str.replace(',', '.')
                amount = float(amount_str)
                if amount > 0 and amount < 100000:  # Reasonable amount range
                    result["amount"] = amount
                    break
            except ValueError:
                continue
    
    return result

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
        voucher_start = datetime.fromisoformat(data.voucher_start_date.replace('Z', '+00:00'))
        refund_start = datetime.fromisoformat(data.refund_start_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Ensure refund date is not before voucher start date
    if refund_start < voucher_start:
        raise HTTPException(status_code=400, detail="Refund date cannot be before voucher start date")
    
    # Custom duration mapping: 1 week=8 days, 2 weeks=15 days, 3 weeks=22 days, 4 weeks=32 days
    duration_days_map = {1: 8, 2: 15, 3: 22, 4: 32}
    total_days = duration_days_map[data.duration_weeks]
    daily_rate = data.amount / total_days
    
    # Calculate days from voucher_start to refund_start
    days_used = (refund_start - voucher_start).days
    
    # Cap days used at total days
    if days_used > total_days:
        days_used = total_days
    
    days_remaining = total_days - days_used
    refund_amount = round(daily_rate * days_remaining, 2)
    
    return RefundResponse(
        original_amount=data.amount,
        duration_weeks=data.duration_weeks,
        total_days=total_days,
        voucher_start_date=data.voucher_start_date,
        refund_start_date=data.refund_start_date,
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

# ==================== DISTRIBUTOR AUTH ROUTES ====================

@api_router.post("/distributor/register", response_model=TokenResponse)
async def register_distributor(data: DistributorCreate):
    existing = await db.distributors.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    distributor_doc = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "email": data.email,
        "phone": data.phone,
        "password": hash_password(data.password),
        "is_active": True,
        "total_sales": 0.0,
        "total_commission": 0.0,
        "pending_commission": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.distributors.insert_one(distributor_doc)
    
    token = create_distributor_token(data.email, distributor_doc["id"])
    return TokenResponse(access_token=token)

@api_router.post("/distributor/login", response_model=TokenResponse)
async def login_distributor(data: DistributorLogin):
    distributor = await db.distributors.find_one({"email": data.email})
    if not distributor or not verify_password(data.password, distributor["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not distributor.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account is disabled")
    
    token = create_distributor_token(data.email, distributor["id"])
    return TokenResponse(access_token=token)

@api_router.get("/distributor/me")
async def get_current_distributor(dist_info: dict = Depends(verify_distributor_token)):
    distributor = await db.distributors.find_one(
        {"id": dist_info["distributor_id"]}, 
        {"_id": 0, "password": 0}
    )
    if not distributor:
        raise HTTPException(status_code=404, detail="Distributor not found")
    return distributor

# ==================== DISTRIBUTOR PROOF OF PAYMENT ROUTES ====================

@api_router.post("/distributor/proofs")
async def upload_proof_of_payment(
    files: List[UploadFile] = File(...),
    customer_phone: str = Form(None),
    notes: str = Form(None),
    dist_info: dict = Depends(verify_distributor_token)
):
    """Upload multiple proofs of payment by distributor - auto-extracts reference and amount"""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per upload")
    
    allowed_types = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
    
    # Get distributor info
    distributor = await db.distributors.find_one({"id": dist_info["distributor_id"]}, {"_id": 0})
    
    results = []
    successful = 0
    failed = 0
    
    for file in files:
        try:
            # Validate file type
            if file.content_type not in allowed_types:
                results.append({
                    "file_name": file.filename,
                    "success": False,
                    "error": "Invalid file type. Must be image or PDF"
                })
                failed += 1
                continue
            
            # Read file content
            file_content = await file.read()
            file_base64 = base64.b64encode(file_content).decode()
            
            # Extract reference and amount from file
            if file.content_type == "application/pdf":
                extracted = extract_from_proof_pdf(file_content)
            else:
                extracted = extract_from_proof_image(file_content)
            
            if not extracted["reference"] and not extracted["amount"]:
                results.append({
                    "file_name": file.filename,
                    "success": False,
                    "error": "Could not extract reference or amount from file"
                })
                failed += 1
                continue
            
            proof_doc = {
                "id": str(uuid.uuid4()),
                "distributor_id": dist_info["distributor_id"],
                "distributor_name": distributor["name"] if distributor else "Unknown",
                "reference": extracted["reference"] or "UNKNOWN",
                "amount": extracted["amount"] or 0.0,
                "customer_phone": customer_phone,
                "notes": notes,
                "file_type": file.content_type,
                "file_name": file.filename,
                "file_data": file_base64,
                "status": "pending",
                "matched_at": None,
                "extracted_text": extracted.get("raw_text", "")[:200],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.proofs_of_payment.insert_one(proof_doc)
            
            results.append({
                "file_name": file.filename,
                "success": True,
                "proof_id": proof_doc["id"],
                "extracted_reference": extracted["reference"],
                "extracted_amount": extracted["amount"],
                "commission": round((extracted["amount"] or 0) * COMMISSION_RATE, 2)
            })
            successful += 1
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            results.append({
                "file_name": file.filename,
                "success": False,
                "error": "Processing error"
            })
            failed += 1
    
    return {
        "message": f"Processed {len(files)} files: {successful} successful, {failed} failed",
        "successful": successful,
        "failed": failed,
        "results": results
    }

@api_router.get("/distributor/proofs")
async def get_distributor_proofs(dist_info: dict = Depends(verify_distributor_token)):
    """Get all proofs uploaded by current distributor"""
    proofs = await db.proofs_of_payment.find(
        {"distributor_id": dist_info["distributor_id"]},
        {"_id": 0, "file_data": 0}
    ).sort("created_at", -1).to_list(100)
    return proofs

@api_router.get("/distributor/commission")
async def get_distributor_commission(dist_info: dict = Depends(verify_distributor_token)):
    """Get commission summary for current distributor"""
    distributor = await db.distributors.find_one(
        {"id": dist_info["distributor_id"]},
        {"_id": 0, "password": 0}
    )
    
    # Count proofs
    matched_count = await db.proofs_of_payment.count_documents({
        "distributor_id": dist_info["distributor_id"],
        "status": "matched"
    })
    pending_count = await db.proofs_of_payment.count_documents({
        "distributor_id": dist_info["distributor_id"],
        "status": "pending"
    })
    
    # Calculate totals from matched proofs
    matched_proofs = await db.proofs_of_payment.find({
        "distributor_id": dist_info["distributor_id"],
        "status": "matched"
    }, {"_id": 0, "amount": 1}).to_list(1000)
    
    total_sales = sum(p["amount"] for p in matched_proofs)
    total_commission = total_sales * COMMISSION_RATE
    
    # Get paid commission from payouts
    payouts = await db.commission_payouts.find({
        "distributor_id": dist_info["distributor_id"],
        "status": "paid"
    }, {"_id": 0, "amount": 1}).to_list(1000)
    
    paid_commission = sum(p["amount"] for p in payouts)
    pending_commission = total_commission - paid_commission
    
    return {
        "distributor_id": dist_info["distributor_id"],
        "distributor_name": distributor["name"] if distributor else "Unknown",
        "total_matched_sales": total_sales,
        "commission_rate": COMMISSION_RATE,
        "total_commission": round(total_commission, 2),
        "paid_commission": round(paid_commission, 2),
        "pending_commission": round(max(0, pending_commission), 2),
        "matched_proofs": matched_count,
        "pending_proofs": pending_count
    }

# ==================== ADMIN DISTRIBUTOR MANAGEMENT ====================

@api_router.get("/admin/distributors")
async def get_all_distributors(email: str = Depends(verify_token)):
    """Get all distributors (admin only)"""
    distributors = await db.distributors.find({}, {"_id": 0, "password": 0}).to_list(1000)
    
    # Calculate stats for each distributor
    for dist in distributors:
        matched_proofs = await db.proofs_of_payment.find({
            "distributor_id": dist["id"],
            "status": "matched"
        }, {"_id": 0, "amount": 1}).to_list(1000)
        
        total_sales = sum(p["amount"] for p in matched_proofs)
        total_commission = total_sales * COMMISSION_RATE
        
        payouts = await db.commission_payouts.find({
            "distributor_id": dist["id"],
            "status": "paid"
        }, {"_id": 0, "amount": 1}).to_list(1000)
        
        paid_commission = sum(p["amount"] for p in payouts)
        
        dist["total_sales"] = round(total_sales, 2)
        dist["total_commission"] = round(total_commission, 2)
        dist["pending_commission"] = round(max(0, total_commission - paid_commission), 2)
    
    return distributors

@api_router.get("/admin/distributors/{distributor_id}")
async def get_distributor(distributor_id: str, email: str = Depends(verify_token)):
    """Get single distributor details"""
    distributor = await db.distributors.find_one({"id": distributor_id}, {"_id": 0, "password": 0})
    if not distributor:
        raise HTTPException(status_code=404, detail="Distributor not found")
    return distributor

@api_router.put("/admin/distributors/{distributor_id}")
async def update_distributor(distributor_id: str, data: DistributorUpdate, email: str = Depends(verify_token)):
    """Update distributor (admin only)"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.distributors.update_one({"id": distributor_id}, {"$set": update_data})
    
    distributor = await db.distributors.find_one({"id": distributor_id}, {"_id": 0, "password": 0})
    return distributor

@api_router.delete("/admin/distributors/{distributor_id}")
async def delete_distributor(distributor_id: str, email: str = Depends(verify_token)):
    """Delete distributor (admin only)"""
    result = await db.distributors.delete_one({"id": distributor_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Distributor not found")
    return {"message": "Distributor deleted"}

# ==================== ADMIN PROOF OF PAYMENT MANAGEMENT ====================

@api_router.get("/admin/proofs")
async def get_all_proofs(status: str = None, email: str = Depends(verify_token)):
    """Get all proofs of payment (admin only)"""
    query = {}
    if status:
        query["status"] = status
    
    proofs = await db.proofs_of_payment.find(query, {"_id": 0, "file_data": 0}).sort("created_at", -1).to_list(500)
    return proofs

@api_router.get("/admin/proofs/{proof_id}")
async def get_proof_detail(proof_id: str, email: str = Depends(verify_token)):
    """Get proof details including file"""
    proof = await db.proofs_of_payment.find_one({"id": proof_id}, {"_id": 0})
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    return proof

@api_router.put("/admin/proofs/{proof_id}/status")
async def update_proof_status(proof_id: str, status: str, email: str = Depends(verify_token)):
    """Update proof status (admin only)"""
    if status not in ["pending", "matched", "paid", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    update_data = {"status": status}
    if status == "matched":
        update_data["matched_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.proofs_of_payment.update_one({"id": proof_id}, {"$set": update_data})
    return {"message": f"Proof status updated to {status}"}

# ==================== BANK STATEMENT & MATCHING ====================

@api_router.post("/admin/bank-statement/upload")
async def upload_bank_statement(
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload bank statement PDF and extract entries"""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    file_content = await file.read()
    entries = parse_bank_statement_pdf(file_content)
    
    # Store bank statement
    statement_doc = {
        "id": str(uuid.uuid4()),
        "file_name": file.filename,
        "entries_count": len(entries),
        "entries": entries,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    await db.bank_statements.insert_one(statement_doc)
    
    return {
        "message": "Bank statement uploaded",
        "statement_id": statement_doc["id"],
        "entries_found": len(entries),
        "entries": entries[:20]  # Return first 20 for preview
    }

@api_router.get("/admin/bank-statements")
async def get_bank_statements(email: str = Depends(verify_token)):
    """Get all uploaded bank statements"""
    statements = await db.bank_statements.find({}, {"_id": 0, "entries": 0}).sort("uploaded_at", -1).to_list(50)
    return statements

@api_router.get("/admin/bank-statements/{statement_id}")
async def get_bank_statement(statement_id: str, email: str = Depends(verify_token)):
    """Get bank statement with entries"""
    statement = await db.bank_statements.find_one({"id": statement_id}, {"_id": 0})
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement

@api_router.post("/admin/match-proofs")
async def match_proofs_to_statement(statement_id: str, email: str = Depends(verify_token)):
    """Match pending proofs against bank statement entries"""
    statement = await db.bank_statements.find_one({"id": statement_id})
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    
    # Get pending proofs
    pending_proofs = await db.proofs_of_payment.find({"status": "pending"}, {"_id": 0}).to_list(1000)
    
    matched_count = 0
    matches = []
    
    for proof in pending_proofs:
        proof_ref = proof["reference"].upper().strip().replace('_', ' ')
        proof_amount = proof["amount"]
        
        for entry in statement.get("entries", []):
            entry_ref = entry["reference"].upper().strip().replace('_', ' ')
            entry_amount = entry["amount"]
            
            # Match by checking if reference names match (partial match allowed)
            # E.g., "BUTHELEZI" matches "S_BUTHELEZI" or "S BUTHELEZI"
            ref_match = False
            
            # Check if entry reference is contained in proof reference or vice versa
            proof_words = proof_ref.split()
            entry_words = entry_ref.split()
            
            # Check if any significant word matches (usually surname)
            for pw in proof_words:
                if len(pw) >= 3:  # Only check words with 3+ chars
                    for ew in entry_words:
                        if len(ew) >= 3:
                            if pw in ew or ew in pw or pw == ew:
                                ref_match = True
                                break
                    if ref_match:
                        break
            
            # Also check direct containment
            if not ref_match:
                if entry_ref in proof_ref or proof_ref in entry_ref:
                    ref_match = True
            
            # If reference matches, check amount (allow small difference)
            if ref_match and abs(proof_amount - entry_amount) < 1.0:
                # Update proof status
                await db.proofs_of_payment.update_one(
                    {"id": proof["id"]},
                    {"$set": {
                        "status": "matched",
                        "matched_at": datetime.now(timezone.utc).isoformat(),
                        "matched_entry": entry
                    }}
                )
                matched_count += 1
                matches.append({
                    "proof_id": proof["id"],
                    "proof_reference": proof["reference"],
                    "proof_amount": proof_amount,
                    "statement_reference": entry["reference"],
                    "statement_amount": entry_amount,
                    "distributor_name": proof.get("distributor_name", "Unknown")
                })
                break
    
    return {
        "message": f"Matched {matched_count} proofs",
        "matched_count": matched_count,
        "matches": matches
    }

# ==================== COMMISSION MANAGEMENT ====================

@api_router.get("/admin/commission/summary")
async def get_commission_summary(email: str = Depends(verify_token)):
    """Get commission summary for all distributors"""
    distributors = await db.distributors.find({}, {"_id": 0, "password": 0}).to_list(1000)
    
    summaries = []
    for dist in distributors:
        matched_proofs = await db.proofs_of_payment.find({
            "distributor_id": dist["id"],
            "status": "matched"
        }, {"_id": 0, "amount": 1}).to_list(1000)
        
        pending_proofs_count = await db.proofs_of_payment.count_documents({
            "distributor_id": dist["id"],
            "status": "pending"
        })
        
        total_sales = sum(p["amount"] for p in matched_proofs)
        total_commission = total_sales * COMMISSION_RATE
        
        payouts = await db.commission_payouts.find({
            "distributor_id": dist["id"],
            "status": "paid"
        }, {"_id": 0, "amount": 1}).to_list(1000)
        
        paid_commission = sum(p["amount"] for p in payouts)
        
        summaries.append({
            "distributor_id": dist["id"],
            "distributor_name": dist["name"],
            "total_matched_sales": round(total_sales, 2),
            "commission_rate": COMMISSION_RATE,
            "total_commission": round(total_commission, 2),
            "paid_commission": round(paid_commission, 2),
            "pending_commission": round(max(0, total_commission - paid_commission), 2),
            "matched_proofs": len(matched_proofs),
            "pending_proofs": pending_proofs_count
        })
    
    return summaries

@api_router.post("/admin/commission/payout")
async def create_commission_payout(
    distributor_id: str,
    amount: float,
    email: str = Depends(verify_token)
):
    """Record commission payout to distributor"""
    distributor = await db.distributors.find_one({"id": distributor_id})
    if not distributor:
        raise HTTPException(status_code=404, detail="Distributor not found")
    
    payout_doc = {
        "id": str(uuid.uuid4()),
        "distributor_id": distributor_id,
        "distributor_name": distributor["name"],
        "amount": amount,
        "status": "paid",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.commission_payouts.insert_one(payout_doc)
    
    return {
        "message": "Payout recorded",
        "payout_id": payout_doc["id"],
        "amount": amount
    }

@api_router.get("/admin/commission/payouts")
async def get_commission_payouts(distributor_id: str = None, email: str = Depends(verify_token)):
    """Get all commission payouts"""
    query = {}
    if distributor_id:
        query["distributor_id"] = distributor_id
    
    payouts = await db.commission_payouts.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return payouts

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
