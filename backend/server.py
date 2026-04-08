from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Request
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
import httpx
from hashlib import md5
import urllib.parse

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# BulkSMS API Configuration (must be after load_dotenv)
BULKSMS_TOKEN_ID = os.environ.get('BULKSMS_TOKEN_ID', '')
BULKSMS_TOKEN_SECRET = os.environ.get('BULKSMS_TOKEN_SECRET', '')
BULKSMS_BASE_URL = "https://api.bulksms.com/v1"

# PayFast Configuration
PAYFAST_MERCHANT_ID = os.environ.get('PAYFAST_MERCHANT_ID', '')
PAYFAST_MERCHANT_KEY = os.environ.get('PAYFAST_MERCHANT_KEY', '')
PAYFAST_PASSPHRASE = os.environ.get('PAYFAST_PASSPHRASE', '')
PAYFAST_SANDBOX_MODE = os.environ.get('PAYFAST_SANDBOX_MODE', 'false').lower() == 'true'
PAYFAST_URL = "https://sandbox.payfast.co.za" if PAYFAST_SANDBOX_MODE else "https://www.payfast.co.za"

# Read the app base URL for PayFast return/notify URLs
def get_base_url():
    """Get the public base URL for callbacks"""
    val = os.environ.get('REACT_APP_BACKEND_URL', '')
    if val:
        return val
    # Fallback: read from frontend .env
    try:
        fe_env = Path(__file__).parent.parent / 'frontend' / '.env'
        for line in fe_env.read_text().splitlines():
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return ''

APP_BASE_URL = get_base_url()

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

# ==================== PORTAL CUSTOMER MODELS ====================

class PortalCustomerRegister(BaseModel):
    name: str
    phone: str
    password: str
    accommodation: str
    referral_code: Optional[str] = None

class PortalCustomerLogin(BaseModel):
    phone: str
    password: str

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
    "1_day": 10.0,
    "1dev_1week": 60.0,
    "1dev_2weeks": 90.0,
    "1dev_3weeks": 120.0,
    "1dev_4weeks": 150.0,
    "2dev_1week": 90.0,
    "2dev_2weeks": 135.0,
    "2dev_3weeks": 180.0,
    "2dev_4weeks": 210.0,
    "3_devices": 200.0,
    "4_devices": 300.0,
    "test": 10.0
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

# Portal customer auth helpers
def create_portal_token(phone: str, customer_id: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": phone,
        "customer_id": customer_id,
        "role": "portal_customer",
        "exp": expiration,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def verify_portal_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "portal_customer":
            raise HTTPException(status_code=401, detail="Invalid portal token")
        return {
            "phone": payload.get("sub"),
            "customer_id": payload.get("customer_id")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Reward tiers: points needed to redeem a free voucher
REWARD_TIERS = {
    "1_day": 10,
    "1dev_1week": 50,
    "1dev_2weeks": 80,
    "1dev_3weeks": 100,
    "1dev_4weeks": 130,
    "2dev_1week": 80,
    "2dev_2weeks": 120,
    "2dev_3weeks": 160,
    "2dev_4weeks": 190,
}

REFERRAL_BONUS_POINTS = 5

ACCOMMODATIONS = [
    "MAJOALE ROOMS",
    "MAJOLA ROOMS",
    "91 CENTURY",
    "MAHLASELA ROOMS",
    "KB STUDENT ACCOMMODATION",
    "MOKOEPA CLUBVIEW ESTATE",
    "CPHOMUS STUDENT ACCOMODATION",
]

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

# ==================== PAYFAST HELPERS ====================

PAYFAST_SIGNATURE_FIELDS = [
    "merchant_id", "merchant_key", "return_url", "cancel_url", "notify_url",
    "name_first", "name_last", "email_address", "cell_number",
    "m_payment_id", "amount", "item_name", "item_description",
    "custom_str1", "custom_str2", "custom_str3", "custom_str4", "custom_str5",
    "custom_int1", "custom_int2", "custom_int3", "custom_int4", "custom_int5",
    "email_confirmation", "confirmation_address", "payment_method",
]

def generate_payfast_signature(data: dict) -> str:
    """Generate MD5 signature for PayFast transaction"""
    params = []
    for field in PAYFAST_SIGNATURE_FIELDS:
        if field in data and data[field] is not None and str(data[field]).strip() != "":
            params.append(f"{field}={urllib.parse.quote_plus(str(data[field]).strip())}")
    
    signature_string = "&".join(params)
    if PAYFAST_PASSPHRASE:
        signature_string += f"&passphrase={urllib.parse.quote_plus(PAYFAST_PASSPHRASE)}"
    
    return md5(signature_string.encode()).hexdigest()

def validate_payfast_signature(itn_data: dict) -> bool:
    """Validate ITN callback signature from PayFast"""
    received_sig = itn_data.get("signature", "").lower()
    # Filter out signature and empty values
    filtered = {k: v.strip() for k, v in itn_data.items() if k != "signature" and v and str(v).strip()}
    
    # Sort alphabetically as per PayFast ITN docs
    params = []
    for key in sorted(filtered.keys()):
        params.append(f"{key}={urllib.parse.quote_plus(str(filtered[key]))}")
    
    sig_string = "&".join(params)
    if PAYFAST_PASSPHRASE:
        sig_string += f"&passphrase={urllib.parse.quote_plus(PAYFAST_PASSPHRASE)}"
    
    expected_sig = md5(sig_string.encode()).hexdigest()
    if expected_sig == received_sig:
        return True
    
    # Fallback: try without URL encoding (some PayFast versions)
    params_raw = []
    for key in sorted(filtered.keys()):
        params_raw.append(f"{key}={str(filtered[key])}")
    sig_raw = "&".join(params_raw)
    if PAYFAST_PASSPHRASE:
        sig_raw += f"&passphrase={PAYFAST_PASSPHRASE}"
    if md5(sig_raw.encode()).hexdigest() == received_sig:
        return True
    
    return False

async def validate_payfast_server(itn_data: dict) -> bool:
    """Validate ITN by querying PayFast server (server-to-server validation)"""
    try:
        pf_url = "https://www.payfast.co.za/eng/query/validate" if not PAYFAST_SANDBOX_MODE else "https://sandbox.payfast.co.za/eng/query/validate"
        
        # Build the param string from ITN data
        filtered = {k: v.strip() for k, v in itn_data.items() if v and str(v).strip()}
        
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                pf_url,
                data=filtered,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15.0
            )
            return response.text.strip() == "VALID"
    except Exception as e:
        logger.error(f"PayFast server validation error: {str(e)}")
        return False

# ==================== BULKSMS MESSAGING FUNCTIONS ====================

def format_phone_international(phone_number: str) -> str:
    """Convert South African local phone number to international format (+27...)"""
    clean = phone_number.strip().replace(" ", "").replace("-", "")
    if clean.startswith('+'):
        return clean
    if clean.startswith('0'):
        return '+27' + clean[1:]
    if clean.startswith('27'):
        return '+' + clean
    return '+27' + clean

import asyncio

async def send_bulksms_message(phone_number: str, message: str) -> dict:
    """Send SMS via BulkSMS API with retry on NOT_SENT"""
    if not BULKSMS_TOKEN_ID or not BULKSMS_TOKEN_SECRET:
        logger.error("BulkSMS credentials not configured")
        return {"success": False, "error": "BulkSMS credentials not configured"}

    international_phone = format_phone_international(phone_number)
    credentials = f"{BULKSMS_TOKEN_ID}:{BULKSMS_TOKEN_SECRET}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_creds}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": international_phone,
        "body": message
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"{BULKSMS_BASE_URL}/messages",
                    json=payload,
                    headers=headers,
                    timeout=15.0
                )

                if response.status_code in (200, 201):
                    resp_data = response.json()
                    # Check if message was actually accepted (not NOT_SENT)
                    msg_id = resp_data[0]["id"] if isinstance(resp_data, list) and resp_data else None
                    if msg_id:
                        # Brief wait then verify delivery status
                        await asyncio.sleep(3)
                        status_resp = await http_client.get(
                            f"{BULKSMS_BASE_URL}/messages/{msg_id}",
                            headers=headers,
                            timeout=10.0
                        )
                        if status_resp.status_code == 200:
                            status_data = status_resp.json()
                            status_type = status_data.get("status", {}).get("type", "")
                            if status_type == "FAILED":
                                logger.warning(f"BulkSMS NOT_SENT on attempt {attempt+1}, retrying after delay...")
                                await asyncio.sleep(5 * (attempt + 1))
                                continue
                    logger.info(f"BulkSMS sent to {international_phone}: msg_id={msg_id}")
                    return {"success": True, "data": resp_data}
                elif response.status_code == 403:
                    error_text = response.text[:300]
                    logger.error(f"BulkSMS quota/auth error: {error_text}")
                    return {"success": False, "error": "BulkSMS daily quota exceeded. Please increase your quota at bulksms.com"}
                else:
                    error_text = response.text[:300]
                    logger.error(f"BulkSMS error {response.status_code}: {error_text}")
                    return {"success": False, "error": f"BulkSMS HTTP {response.status_code}: {error_text}"}

        except Exception as e:
            logger.error(f"BulkSMS API error attempt {attempt+1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
                continue
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "SMS failed after retries (BulkSMS rate limit)"}

async def send_bulksms_bulk(phone_numbers: list, message: str) -> dict:
    """Send SMS to multiple recipients via BulkSMS API"""
    if not BULKSMS_TOKEN_ID or not BULKSMS_TOKEN_SECRET:
        return {"success": False, "error": "BulkSMS credentials not configured"}

    credentials = f"{BULKSMS_TOKEN_ID}:{BULKSMS_TOKEN_SECRET}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_creds}",
        "Content-Type": "application/json"
    }

    messages = [
        {"to": format_phone_international(phone), "body": message}
        for phone in phone_numbers
    ]

    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{BULKSMS_BASE_URL}/messages",
                json=messages,
                headers=headers,
                timeout=30.0
            )

            if response.status_code in (200, 201):
                resp_data = response.json()
                logger.info(f"BulkSMS bulk sent to {len(phone_numbers)} recipients")
                return {"success": True, "data": resp_data}
            else:
                error_text = response.text[:300]
                logger.error(f"BulkSMS bulk error {response.status_code}: {error_text}")
                return {"success": False, "error": f"BulkSMS HTTP {response.status_code}: {error_text}"}

    except Exception as e:
        logger.error(f"BulkSMS bulk API error: {str(e)}")
        return {"success": False, "error": str(e)}

async def send_payment_reminder_sms(customer_name: str, phone: str, amount: float, voucher_code: str) -> dict:
    """Send payment reminder via BulkSMS"""
    message = f"Hi {customer_name}, your WiFi subscription of R{amount:.2f} is due at month end. Voucher: {voucher_code}. Pay to avoid interruption. Thank you!"
    return await send_bulksms_message(phone, message)

async def send_voucher_code_sms(customer_name: str, phone: str, voucher_code: str, plan: str) -> dict:
    """Send voucher code via BulkSMS"""
    message = f"Hi {customer_name}, your WiFi voucher code: {voucher_code} (Plan: {plan}). Enjoy your internet!"
    return await send_bulksms_message(phone, message)

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

@api_router.get("/dashboard/analytics")
async def get_dashboard_analytics(email: str = Depends(verify_token)):
    """Revenue per location, monthly growth, average spend per user"""
    
    # Revenue per location (accommodation)
    all_payments = await db.payments.find({"status": "complete"}, {"_id": 0}).to_list(5000)
    portal_users = await db.portal_customers.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    
    # Build lookup: portal_customer_id -> accommodation
    user_acc_map = {u["id"]: u.get("accommodation", "Unknown") or "Unknown" for u in portal_users}
    
    # Revenue per location
    location_revenue = {}
    for p in all_payments:
        acc = p.get("accommodation") or user_acc_map.get(p.get("portal_customer_id"), "Unknown") or "Unknown"
        location_revenue[acc] = location_revenue.get(acc, 0) + (p.get("amount", 0) or 0)
    
    revenue_by_location = [
        {"location": loc, "revenue": rev, "count": sum(1 for p in all_payments if (p.get("accommodation") or user_acc_map.get(p.get("portal_customer_id"), "Unknown") or "Unknown") == loc)}
        for loc, rev in sorted(location_revenue.items(), key=lambda x: -x[1])
    ]
    
    # Monthly growth (last 6 months of payments)
    monthly_data = {}
    for p in all_payments:
        created = p.get("created_at", "")
        if created:
            month_key = created[:7]  # "2026-03"
            if month_key not in monthly_data:
                monthly_data[month_key] = {"revenue": 0, "count": 0}
            monthly_data[month_key]["revenue"] += p.get("amount", 0) or 0
            monthly_data[month_key]["count"] += 1
    
    sorted_months = sorted(monthly_data.keys())[-6:]
    monthly_growth = []
    for i, month in enumerate(sorted_months):
        entry = {"month": month, "revenue": monthly_data[month]["revenue"], "purchases": monthly_data[month]["count"]}
        if i > 0:
            prev = monthly_data[sorted_months[i - 1]]["revenue"]
            entry["growth_pct"] = round(((entry["revenue"] - prev) / prev * 100) if prev else 0, 1)
        else:
            entry["growth_pct"] = 0
        monthly_growth.append(entry)
    
    # Average spend per user
    user_spending = {}
    for p in all_payments:
        uid = p.get("portal_customer_id")
        if uid:
            user_spending[uid] = user_spending.get(uid, 0) + (p.get("amount", 0) or 0)
    
    total_users_with_purchases = len(user_spending)
    total_revenue = sum(user_spending.values())
    avg_spend = round(total_revenue / total_users_with_purchases, 2) if total_users_with_purchases else 0
    
    return {
        "revenue_by_location": revenue_by_location,
        "monthly_growth": monthly_growth,
        "avg_spend_per_user": avg_spend,
        "total_paying_users": total_users_with_purchases,
        "total_revenue": total_revenue,
    }

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

# ==================== ADMIN PORTAL USERS MANAGEMENT ====================

@api_router.get("/admin/portal-users")
async def get_all_portal_users(
    date_from: str = None,
    date_to: str = None,
    email: str = Depends(verify_token)
):
    """Admin: Get all customers (merged portal + legacy) with purchases, points, and redemptions"""
    # Fetch from both collections
    portal_custs = await db.portal_customers.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(1000)
    legacy_custs = await db.customers.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Track portal phones to avoid duplicates
    portal_phones = {c.get("phone", "").strip() for c in portal_custs}
    
    # Build date filter for purchases
    purchase_date_filter = {}
    if date_from:
        purchase_date_filter["$gte"] = date_from
    if date_to:
        purchase_date_filter["$lte"] = date_to + "T23:59:59"
    
    result = []
    
    # Process portal customers
    for cust in portal_custs:
        cid = cust["id"]
        
        all_purchases = await db.payments.find(
            {"portal_customer_id": cid, "status": "complete"}, {"_id": 0}
        ).sort("created_at", -1).to_list(500)
        
        if purchase_date_filter:
            filtered_purchases = [
                p for p in all_purchases
                if (not date_from or p.get("created_at", "") >= date_from) and
                   (not date_to or p.get("created_at", "") <= date_to + "T23:59:59")
            ]
        else:
            filtered_purchases = all_purchases
        
        points_history = await db.points_history.find({"customer_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(100)
        redemptions = [p for p in points_history if p.get("type") == "redeemed"]
        
        lifetime_spent = sum(p.get("amount", 0) for p in all_purchases)
        filtered_spent = sum(p.get("amount", 0) for p in filtered_purchases)
        total_points_earned = sum(p["points"] for p in points_history if p.get("points", 0) > 0)
        total_points_redeemed = abs(sum(p["points"] for p in points_history if p.get("points", 0) < 0))
        
        # Get latest voucher from purchases
        latest_voucher = next((p.get("voucher_code") for p in all_purchases if p.get("voucher_code")), None)
        latest_plan = next((p.get("plan") for p in all_purchases if p.get("plan")), None)
        
        result.append({
            "id": cid,
            "name": cust.get("name", ""),
            "phone": cust.get("phone", ""),
            "accommodation": cust.get("accommodation", ""),
            "points": cust.get("points", 0),
            "referral_code": cust.get("referral_code", ""),
            "referred_by": cust.get("referred_by"),
            "created_at": cust.get("created_at", ""),
            "source": "portal",
            "is_active": True,
            "voucher_code": latest_voucher,
            "plan": latest_plan,
            "total_spent": filtered_spent,
            "total_purchases": len(filtered_purchases),
            "lifetime_spent": lifetime_spent,
            "lifetime_purchases": len(all_purchases),
            "total_points_earned": total_points_earned,
            "total_points_redeemed": total_points_redeemed,
            "purchases": all_purchases,
            "points_history": points_history,
            "redemptions": redemptions,
        })
    
    # Process legacy customers (skip duplicates by phone)
    for cust in legacy_custs:
        phone = cust.get("phone", "").strip()
        if phone in portal_phones:
            continue
        
        result.append({
            "id": cust.get("id", ""),
            "name": cust.get("name", ""),
            "phone": phone,
            "accommodation": "",
            "points": 0,
            "referral_code": "",
            "referred_by": None,
            "created_at": cust.get("created_at", cust.get("start_date", "")),
            "source": "legacy",
            "is_active": cust.get("is_active", True),
            "voucher_code": cust.get("voucher_code", ""),
            "plan": cust.get("plan", ""),
            "total_spent": 0,
            "total_purchases": 0,
            "lifetime_spent": 0,
            "lifetime_purchases": 0,
            "total_points_earned": 0,
            "total_points_redeemed": 0,
            "purchases": [],
            "points_history": [],
            "redemptions": [],
        })
    
    return result

@api_router.get("/admin/portal-users/{customer_id}")
async def get_portal_user_detail(customer_id: str, email: str = Depends(verify_token)):
    """Admin: Get single portal customer detail"""
    cust = await db.portal_customers.find_one({"id": customer_id}, {"_id": 0, "password_hash": 0})
    if not cust:
        raise HTTPException(status_code=404, detail="Portal user not found")
    
    purchases = await db.payments.find(
        {"portal_customer_id": customer_id, "status": "complete"}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    points_history = await db.points_history.find(
        {"customer_id": customer_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    redemptions = [p for p in points_history if p.get("type") == "redeemed"]
    total_spent = sum(p.get("amount", 0) for p in purchases)
    
    return {
        **cust,
        "total_spent": total_spent,
        "total_purchases": len(purchases),
        "purchases": purchases,
        "points_history": points_history,
        "redemptions": redemptions,
    }

class PortalPasswordReset(BaseModel):
    new_password: str

@api_router.post("/admin/portal-users/{customer_id}/reset-password")
async def admin_reset_portal_password(customer_id: str, data: PortalPasswordReset, email: str = Depends(verify_token)):
    """Admin: Reset a portal customer's password"""
    cust = await db.portal_customers.find_one({"id": customer_id})
    if not cust:
        raise HTTPException(status_code=404, detail="Portal user not found")
    
    new_hash = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
    await db.portal_customers.update_one({"id": customer_id}, {"$set": {"password_hash": new_hash}})
    
    return {"message": f"Password reset for {cust['name']}", "success": True}

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

# ==================== SMS MESSAGING ROUTES (BulkSMS) ====================

class SendReminderRequest(BaseModel):
    customer_id: str
    channel: str = "sms"

class SendVoucherRequest(BaseModel):
    customer_id: str
    channel: str = "sms"

class BulkReminderRequest(BaseModel):
    channel: str = "sms"

@api_router.post("/messaging/send-reminder")
async def send_single_reminder(data: SendReminderRequest, email: str = Depends(verify_token)):
    """Send payment reminder to a single customer via BulkSMS"""
    customer = await db.customers.find_one({"id": data.customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    result = await send_payment_reminder_sms(
        customer["name"],
        customer["phone"],
        get_monthly_rate(customer.get("plan", "3_devices")),
        customer["voucher_code"]
    )
    
    log_doc = {
        "id": str(uuid.uuid4()),
        "customer_id": customer["id"],
        "customer_name": customer["name"],
        "customer_phone": customer["phone"],
        "message_type": "payment_reminder",
        "channel": "sms",
        "status": "sent" if result.get("success") else "failed",
        "error": result.get("error") if not result.get("success") else None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.message_logs.insert_one(log_doc)
    
    if result.get("success"):
        return {"message": f"Reminder sent to {customer['name']} via SMS", "success": True}
    else:
        error_msg = result.get("error", "Failed to send SMS")
        raise HTTPException(status_code=400, detail=f"BulkSMS: {error_msg}")

@api_router.post("/messaging/send-voucher")
async def send_voucher_to_customer(data: SendVoucherRequest, email: str = Depends(verify_token)):
    """Send voucher code to a customer via BulkSMS"""
    customer = await db.customers.find_one({"id": data.customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    result = await send_voucher_code_sms(
        customer["name"],
        customer["phone"],
        customer["voucher_code"],
        customer.get("plan", "3_devices")
    )
    
    log_doc = {
        "id": str(uuid.uuid4()),
        "customer_id": customer["id"],
        "customer_name": customer["name"],
        "customer_phone": customer["phone"],
        "message_type": "voucher_code",
        "channel": "sms",
        "status": "sent" if result.get("success") else "failed",
        "error": result.get("error") if not result.get("success") else None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.message_logs.insert_one(log_doc)
    
    if result.get("success"):
        return {"message": f"Voucher sent to {customer['name']} via SMS", "success": True}
    else:
        error_msg = result.get("error", "Failed to send SMS")
        raise HTTPException(status_code=400, detail=f"BulkSMS: {error_msg}")

@api_router.post("/messaging/send-bulk-reminders")
async def send_bulk_reminders(data: BulkReminderRequest, email: str = Depends(verify_token)):
    """Send payment reminders to all active customers via BulkSMS"""
    customers = await db.customers.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    sent_count = 0
    failed_count = 0
    errors = []
    
    for i, customer in enumerate(customers):
        if i > 0:
            await asyncio.sleep(2)  # Rate limit: 2s between sends
        result = await send_payment_reminder_sms(
            customer["name"],
            customer["phone"],
            get_monthly_rate(customer.get("plan", "3_devices")),
            customer["voucher_code"]
        )
        
        log_doc = {
            "id": str(uuid.uuid4()),
            "customer_id": customer["id"],
            "customer_name": customer["name"],
            "customer_phone": customer["phone"],
            "message_type": "payment_reminder",
            "channel": "sms",
            "status": "sent" if result.get("success") else "failed",
            "error": result.get("error"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.message_logs.insert_one(log_doc)
        
        if result.get("success"):
            sent_count += 1
        else:
            failed_count += 1
            errors.append({"customer": customer["name"], "error": result.get("error")})
    
    return {
        "message": f"Sent {sent_count} reminders, {failed_count} failed",
        "sent": sent_count,
        "failed": failed_count,
        "errors": errors[:10]
    }

@api_router.get("/messaging/logs")
async def get_message_logs(email: str = Depends(verify_token)):
    """Get message delivery logs"""
    logs = await db.message_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return logs

@api_router.get("/messaging/status")
async def get_messaging_status(email: str = Depends(verify_token)):
    """Check BulkSMS configuration status"""
    is_configured = bool(BULKSMS_TOKEN_ID and BULKSMS_TOKEN_SECRET)
    return {
        "bulksms_configured": is_configured,
        "api_key_set": is_configured,
        "channels_available": ["sms"] if is_configured else []
    }

# ==================== VOUCHER POOL MANAGEMENT (ADMIN) ====================

class VoucherPoolEntry(BaseModel):
    code: str
    plan: str  # "3_devices" or "4_devices"

class VoucherBulkAdd(BaseModel):
    codes: List[str]
    plan: str
    accommodation: str

@api_router.post("/vouchers/add")
async def add_voucher_codes(data: VoucherBulkAdd, email: str = Depends(verify_token)):
    """Admin: Add voucher codes to the pool"""
    if data.plan not in PLAN_RATES:
        raise HTTPException(status_code=400, detail="Invalid plan")
    if data.accommodation not in ACCOMMODATIONS:
        raise HTTPException(status_code=400, detail="Invalid accommodation")
    
    added = 0
    duplicates = 0
    for code in data.codes:
        code = code.strip()
        if not code:
            continue
        existing = await db.voucher_pool.find_one({"code": code})
        if existing:
            duplicates += 1
            continue
        await db.voucher_pool.insert_one({
            "id": str(uuid.uuid4()),
            "code": code,
            "plan": data.plan,
            "accommodation": data.accommodation,
            "assigned": False,
            "assigned_to": None,
            "assigned_at": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        added += 1
    
    return {"message": f"Added {added} voucher codes ({duplicates} duplicates skipped)", "added": added, "duplicates": duplicates}

@api_router.post("/vouchers/upload-csv")
async def upload_voucher_csv(file: UploadFile = File(...), plan: str = Form(...), accommodation: str = Form(...), email: str = Depends(verify_token)):
    """Admin: Upload CSV or PDF file with voucher codes."""
    if plan not in PLAN_RATES:
        raise HTTPException(status_code=400, detail="Invalid plan")
    if accommodation not in ACCOMMODATIONS:
        raise HTTPException(status_code=400, detail="Invalid accommodation")
    
    import csv
    import io
    
    content = await file.read()
    filename = (file.filename or "").lower()
    
    # Extract text based on file type
    if filename.endswith(".pdf"):
        try:
            import pdfplumber
            import re
            pdf = pdfplumber.open(io.BytesIO(content))
            lines = []
            voucher_pattern = re.compile(r'\b(\d{6})\b')
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    for text_line in page_text.strip().splitlines():
                        codes = voucher_pattern.findall(text_line)
                        lines.extend(codes)
            pdf.close()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read PDF: {str(e)}")
    else:
        text = content.decode("utf-8", errors="ignore")
        lines = []
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            if row:
                lines.append(row[0])
    
    added = 0
    duplicates = 0
    skip_words = {"code", "voucher", "voucher_code", "voucher code", ""}
    for line in lines:
        code = line.strip()
        if not code or code.lower() in skip_words:
            continue
        existing = await db.voucher_pool.find_one({"code": code})
        if existing:
            duplicates += 1
            continue
        await db.voucher_pool.insert_one({
            "id": str(uuid.uuid4()),
            "code": code,
            "plan": plan,
            "accommodation": accommodation,
            "assigned": False,
            "assigned_to": None,
            "assigned_at": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        added += 1
    
    return {"message": f"Uploaded {added} voucher codes ({duplicates} duplicates skipped)", "added": added, "duplicates": duplicates}

@api_router.get("/vouchers")
async def get_voucher_pool(email: str = Depends(verify_token)):
    """Admin: Get all voucher codes in the pool"""
    vouchers = await db.voucher_pool.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return vouchers

@api_router.delete("/vouchers/{voucher_id}")
async def delete_voucher(voucher_id: str, email: str = Depends(verify_token)):
    """Admin: Delete an unassigned voucher code"""
    voucher = await db.voucher_pool.find_one({"id": voucher_id})
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    if voucher.get("assigned"):
        raise HTTPException(status_code=400, detail="Cannot delete assigned voucher")
    await db.voucher_pool.delete_one({"id": voucher_id})
    return {"message": "Voucher deleted"}

class BulkDeleteRequest(BaseModel):
    voucher_ids: list

@api_router.post("/vouchers/bulk-delete")
async def bulk_delete_vouchers(data: BulkDeleteRequest, email: str = Depends(verify_token)):
    """Admin: Delete multiple unassigned voucher codes"""
    deleted = 0
    skipped = 0
    for vid in data.voucher_ids:
        voucher = await db.voucher_pool.find_one({"id": vid})
        if voucher and not voucher.get("assigned"):
            await db.voucher_pool.delete_one({"id": vid})
            deleted += 1
        else:
            skipped += 1
    return {"message": f"Deleted {deleted} vouchers, skipped {skipped} (assigned or not found)", "deleted": deleted, "skipped": skipped}

@api_router.get("/vouchers/stats")
async def get_voucher_stats(email: str = Depends(verify_token)):
    """Admin: Get voucher pool stats"""
    result = {}
    for plan_key in PLAN_RATES:
        total = await db.voucher_pool.count_documents({"plan": plan_key})
        available = await db.voucher_pool.count_documents({"plan": plan_key, "assigned": False})
        if total > 0:
            result[plan_key] = {"total": total, "available": available, "assigned": total - available}
    return result

# ==================== PAYFAST PAYMENT ROUTES (PUBLIC) ====================

class PaymentInitiateRequest(BaseModel):
    plan: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    accommodation: Optional[str] = None

@api_router.post("/payment/initiate")
async def initiate_payment(data: PaymentInitiateRequest):
    """Public: Initiate a PayFast payment for a WiFi plan"""
    if data.plan not in PLAN_RATES:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    amount = PLAN_RATES[data.plan]
    plan_labels = {
        "1_day": "1 Day Pass (R10)",
        "1dev_1week": "1 Device 1 Week (R60)",
        "1dev_2weeks": "1 Device 2 Weeks (R90)",
        "1dev_3weeks": "1 Device 3 Weeks (R120)",
        "1dev_4weeks": "1 Device 4 Weeks (R150)",
        "2dev_1week": "2 Devices 1 Week (R90)",
        "2dev_2weeks": "2 Devices 2 Weeks (R135)",
        "2dev_3weeks": "2 Devices 3 Weeks (R180)",
        "2dev_4weeks": "2 Devices 4 Weeks (R210)",
        "3_devices": "3 Devices Monthly (R200)",
        "4_devices": "4 Devices Monthly (R300)",
        "test": "Test Plan (R10)",
    }
    plan_label = plan_labels.get(data.plan, data.plan)
    
    # Check if voucher codes are available
    voucher_query = {"plan": data.plan, "assigned": False}
    if data.accommodation and data.accommodation in ACCOMMODATIONS:
        voucher_query["accommodation"] = data.accommodation
    available = await db.voucher_pool.find_one(voucher_query)
    if not available:
        raise HTTPException(status_code=400, detail="No voucher codes available for this plan. Please contact support.")
    
    # Create payment record
    order_id = f"WF-{uuid.uuid4().hex[:10].upper()}"
    
    # Clean phone number
    phone = data.customer_phone.strip()
    if phone.startswith('0'):
        phone_intl = '27' + phone[1:]
    elif phone.startswith('+27'):
        phone_intl = phone[1:]
    elif phone.startswith('+'):
        phone_intl = phone[1:]
    else:
        phone_intl = phone
    
    base_url = APP_BASE_URL
    
    payment_doc = {
        "id": order_id,
        "plan": data.plan,
        "amount": amount,
        "customer_name": data.customer_name,
        "customer_phone": data.customer_phone,
        "customer_email": data.customer_email or "",
        "accommodation": data.accommodation if data.accommodation in ACCOMMODATIONS else None,
        "status": "pending",
        "voucher_code": None,
        "pf_payment_id": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payments.insert_one(payment_doc)
    
    # Build PayFast form data
    form_data = {
        "merchant_id": PAYFAST_MERCHANT_ID,
        "merchant_key": PAYFAST_MERCHANT_KEY,
        "return_url": f"{base_url}/payment/success?order_id={order_id}",
        "cancel_url": f"{base_url}/payment/cancel",
        "notify_url": f"{base_url}/api/payment/notify",
        "name_first": data.customer_name.split()[0] if data.customer_name else "Customer",
        "email_address": data.customer_email or "customer@wifi.co.za",
        "cell_number": phone_intl,
        "m_payment_id": order_id,
        "amount": f"{amount:.2f}",
        "item_name": f"WiFi Plan - {plan_label}",
        "item_description": f"WiFi Hotspot {plan_label} Monthly",
        "custom_str1": order_id,
        "custom_str2": data.plan,
    }
    
    # Generate signature
    signature = generate_payfast_signature(form_data)
    form_data["signature"] = signature
    
    return {
        "order_id": order_id,
        "payfast_url": f"{PAYFAST_URL}/eng/process",
        "form_fields": form_data
    }

@api_router.post("/payment/notify")
async def payfast_itn_callback(request: Request):
    """PayFast ITN callback - receives payment notification"""
    try:
        form = await request.form()
        itn_data = dict(form)
        
        logger.info(f"PayFast ITN received: {itn_data}")
        
        # Validate: try signature first, then server validation as fallback
        sig_valid = validate_payfast_signature(itn_data)
        if not sig_valid:
            logger.warning("PayFast ITN: Signature mismatch, trying server validation...")
            server_valid = await validate_payfast_server(itn_data)
            if not server_valid:
                # Final fallback: verify merchant_id matches ours
                if itn_data.get("merchant_id") != PAYFAST_MERCHANT_ID:
                    logger.error("PayFast ITN: All validation failed")
                    return {"success": False, "error": "Validation failed"}
                logger.warning("PayFast ITN: Accepted via merchant_id match (sig + server validation failed)")
        
        order_id = itn_data.get("custom_str1") or itn_data.get("m_payment_id")
        payment_status = itn_data.get("payment_status")
        pf_payment_id = itn_data.get("pf_payment_id")
        amount_gross = float(itn_data.get("amount_gross", 0))
        
        # Find payment record
        payment = await db.payments.find_one({"id": order_id})
        if not payment:
            logger.error(f"PayFast ITN: Payment {order_id} not found")
            return {"success": False, "error": "Payment not found"}
        
        # Validate amount
        if abs(payment["amount"] - amount_gross) > 1.0:
            logger.error(f"PayFast ITN: Amount mismatch {payment['amount']} vs {amount_gross}")
            return {"success": False, "error": "Amount mismatch"}
        
        if payment_status == "COMPLETE" and payment["status"] != "complete":
            # Assign a voucher code from the pool
            plan = itn_data.get("custom_str2") or payment["plan"]
            
            # Build voucher query - filter by accommodation if portal customer
            voucher_query = {"plan": plan, "assigned": False}
            if payment.get("portal_customer_id"):
                portal_cust = await db.portal_customers.find_one({"id": payment["portal_customer_id"]})
                if portal_cust and portal_cust.get("accommodation"):
                    voucher_query["accommodation"] = portal_cust["accommodation"]
            elif payment.get("accommodation"):
                voucher_query["accommodation"] = payment["accommodation"]
            
            voucher = await db.voucher_pool.find_one_and_update(
                voucher_query,
                {"$set": {
                    "assigned": True,
                    "assigned_to": order_id,
                    "assigned_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            voucher_code = voucher["code"] if voucher else "CONTACT-SUPPORT"
            
            # Update payment record
            await db.payments.update_one(
                {"id": order_id},
                {"$set": {
                    "status": "complete",
                    "pf_payment_id": pf_payment_id,
                    "voucher_code": voucher_code,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            # Try to send voucher via BulkSMS
            if BULKSMS_TOKEN_ID and payment.get("customer_phone"):
                try:
                    sms_result = await send_voucher_code_sms(
                        payment["customer_name"],
                        payment["customer_phone"],
                        voucher_code,
                        plan
                    )
                    if sms_result.get("success"):
                        logger.info(f"Voucher sent via BulkSMS to {payment['customer_phone']}")
                    else:
                        logger.error(f"BulkSMS failed: {sms_result.get('error')} - Voucher {voucher_code} assigned but SMS not delivered")
                except Exception as sms_err:
                    logger.error(f"BulkSMS send failed: {sms_err}")
            
            logger.info(f"Payment {order_id} completed. Voucher: {voucher_code}")
            
            # Award loyalty points to portal customer (1 point per R10)
            if payment.get("portal_customer_id"):
                points_earned = int(amount_gross / 10)
                if points_earned > 0:
                    await db.portal_customers.update_one(
                        {"id": payment["portal_customer_id"]},
                        {"$inc": {"points": points_earned}}
                    )
                    await db.points_history.insert_one({
                        "id": str(uuid.uuid4()),
                        "customer_id": payment["portal_customer_id"],
                        "points": points_earned,
                        "type": "earned",
                        "description": f"Purchase: {plan} (R{amount_gross})",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    })
                    logger.info(f"Awarded {points_earned} points to portal customer {payment['portal_customer_id']}")
        
        elif payment_status == "FAILED":
            await db.payments.update_one(
                {"id": order_id},
                {"$set": {"status": "failed", "pf_payment_id": pf_payment_id}}
            )
        elif payment_status == "CANCELLED":
            await db.payments.update_one(
                {"id": order_id},
                {"$set": {"status": "cancelled"}}
            )
        
        return {"success": True}
    
    except Exception as e:
        logger.error(f"PayFast ITN error: {str(e)}")
        return {"success": False, "error": str(e)}

@api_router.get("/payment/verify/{order_id}")
async def verify_payment(order_id: str):
    """Public: Verify payment status and get voucher code"""
    payment = await db.payments.find_one({"id": order_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "order_id": payment["id"],
        "status": payment["status"],
        "plan": payment["plan"],
        "amount": payment["amount"],
        "customer_name": payment["customer_name"],
        "voucher_code": payment.get("voucher_code"),
        "completed_at": payment.get("completed_at")
    }

@api_router.get("/admin/payments")
async def get_all_payments(email: str = Depends(verify_token)):
    """Admin: Get all payment records"""
    payments = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return payments

# ==================== CUSTOMER PORTAL ROUTES ====================

@api_router.get("/portal/accommodations")
async def get_accommodations():
    """Public: Get list of available accommodations"""
    return {"accommodations": ACCOMMODATIONS}

@api_router.post("/portal/register")
async def portal_register(data: PortalCustomerRegister):
    """Public: Register a new portal customer"""
    existing = await db.portal_customers.find_one({"phone": data.phone})
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    if data.accommodation not in ACCOMMODATIONS:
        raise HTTPException(status_code=400, detail="Invalid accommodation")
    
    customer_id = str(uuid.uuid4())
    referral_code = f"REF-{uuid.uuid4().hex[:6].upper()}"
    
    doc = {
        "id": customer_id,
        "name": data.name.strip(),
        "phone": data.phone.strip(),
        "password_hash": bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode(),
        "points": 0,
        "accommodation": data.accommodation,
        "referral_code": referral_code,
        "referred_by": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Handle referral
    if data.referral_code and data.referral_code.strip():
        referrer = await db.portal_customers.find_one({"referral_code": data.referral_code.strip().upper()})
        if referrer:
            doc["referred_by"] = referrer["id"]
            # Award bonus points to referrer
            await db.portal_customers.update_one(
                {"id": referrer["id"]},
                {"$inc": {"points": REFERRAL_BONUS_POINTS}}
            )
            await db.points_history.insert_one({
                "id": str(uuid.uuid4()),
                "customer_id": referrer["id"],
                "points": REFERRAL_BONUS_POINTS,
                "type": "referral_bonus",
                "description": f"Referral bonus: {data.name.strip()} joined",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            # Award bonus to new customer too
            doc["points"] = REFERRAL_BONUS_POINTS
    
    await db.portal_customers.insert_one(doc)
    
    # Log referral bonus for new customer if applicable
    if doc["points"] > 0:
        await db.points_history.insert_one({
            "id": str(uuid.uuid4()),
            "customer_id": customer_id,
            "points": REFERRAL_BONUS_POINTS,
            "type": "referral_bonus",
            "description": "Welcome bonus: joined via referral",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    token = create_portal_token(data.phone.strip(), customer_id)
    return {"access_token": token, "token_type": "bearer", "customer_id": customer_id}

@api_router.post("/portal/login")
async def portal_login(data: PortalCustomerLogin):
    """Public: Login as portal customer"""
    customer = await db.portal_customers.find_one({"phone": data.phone.strip()})
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid phone or password")
    if not bcrypt.checkpw(data.password.encode(), customer["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid phone or password")
    
    token = create_portal_token(customer["phone"], customer["id"])
    return {"access_token": token, "token_type": "bearer", "customer_id": customer["id"]}

@api_router.get("/portal/profile")
async def portal_profile(user: dict = Depends(verify_portal_token)):
    """Portal: Get customer profile"""
    customer = await db.portal_customers.find_one({"id": user["customer_id"]}, {"_id": 0, "password_hash": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Count referrals
    referral_count = await db.portal_customers.count_documents({"referred_by": user["customer_id"]})
    customer["referral_count"] = referral_count
    return customer

@api_router.get("/portal/purchases")
async def portal_purchases(user: dict = Depends(verify_portal_token)):
    """Portal: Get purchase history"""
    purchases = await db.payments.find(
        {"portal_customer_id": user["customer_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return purchases

@api_router.get("/portal/points")
async def portal_points(user: dict = Depends(verify_portal_token)):
    """Portal: Get points balance and history"""
    customer = await db.portal_customers.find_one({"id": user["customer_id"]}, {"_id": 0})
    history = await db.points_history.find(
        {"customer_id": user["customer_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"balance": customer.get("points", 0), "history": history}

@api_router.get("/portal/rewards")
async def portal_rewards(user: dict = Depends(verify_portal_token)):
    """Portal: Get available reward tiers"""
    customer = await db.portal_customers.find_one({"id": user["customer_id"]}, {"_id": 0})
    balance = customer.get("points", 0)
    
    plan_labels = {
        "1_day": "1 Day Pass",
        "1dev_1week": "1 Device 1 Week",
        "1dev_2weeks": "1 Device 2 Weeks",
        "1dev_3weeks": "1 Device 3 Weeks",
        "1dev_4weeks": "1 Device 4 Weeks",
        "2dev_1week": "2 Devices 1 Week",
        "2dev_2weeks": "2 Devices 2 Weeks",
        "2dev_3weeks": "2 Devices 3 Weeks",
        "2dev_4weeks": "2 Devices 4 Weeks",
        "3_devices": "3 Devices Monthly",
        "4_devices": "4 Devices Monthly",
    }
    
    tiers = []
    for plan, pts_needed in REWARD_TIERS.items():
        tiers.append({
            "plan": plan,
            "label": plan_labels.get(plan, plan),
            "points_needed": pts_needed,
            "value": PLAN_RATES.get(plan, 0),
            "can_redeem": balance >= pts_needed
        })
    
    return {"balance": balance, "tiers": tiers}

@api_router.post("/portal/redeem")
async def portal_redeem(data: dict, user: dict = Depends(verify_portal_token)):
    """Portal: Redeem points for a free voucher"""
    plan = data.get("plan")
    if plan not in REWARD_TIERS:
        raise HTTPException(status_code=400, detail="Invalid reward plan")
    
    pts_needed = REWARD_TIERS[plan]
    customer = await db.portal_customers.find_one({"id": user["customer_id"]})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if customer.get("points", 0) < pts_needed:
        raise HTTPException(status_code=400, detail=f"Not enough points. Need {pts_needed}, have {customer.get('points', 0)}")
    
    # Find available voucher (filtered by customer's accommodation)
    voucher_query = {"plan": plan, "assigned": False}
    if customer.get("accommodation"):
        voucher_query["accommodation"] = customer["accommodation"]
    
    voucher = await db.voucher_pool.find_one_and_update(
        voucher_query,
        {"$set": {
            "assigned": True,
            "assigned_to": f"REDEEM-{user['customer_id'][:8]}",
            "assigned_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if not voucher:
        raise HTTPException(status_code=400, detail="No voucher codes available for this plan. Contact support.")
    
    # Deduct points
    await db.portal_customers.update_one(
        {"id": user["customer_id"]},
        {"$inc": {"points": -pts_needed}}
    )
    
    # Log points deduction
    await db.points_history.insert_one({
        "id": str(uuid.uuid4()),
        "customer_id": user["customer_id"],
        "points": -pts_needed,
        "type": "redeemed",
        "description": f"Redeemed for {plan}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Create payment record for the redemption
    order_id = f"RDM-{uuid.uuid4().hex[:10].upper()}"
    await db.payments.insert_one({
        "id": order_id,
        "plan": plan,
        "amount": 0,
        "customer_name": customer["name"],
        "customer_phone": customer["phone"],
        "customer_email": "",
        "portal_customer_id": user["customer_id"],
        "status": "complete",
        "voucher_code": voucher["code"],
        "pf_payment_id": None,
        "payment_type": "redemption",
        "points_used": pts_needed,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"voucher_code": voucher["code"], "points_used": pts_needed, "points_remaining": customer.get("points", 0) - pts_needed}

@api_router.post("/portal/payment/initiate")
async def portal_payment_initiate(data: dict, user: dict = Depends(verify_portal_token)):
    """Portal: Initiate PayFast payment (authenticated)"""
    plan = data.get("plan")
    if plan not in PLAN_RATES:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    customer = await db.portal_customers.find_one({"id": user["customer_id"]}, {"_id": 0, "password_hash": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    amount = PLAN_RATES[plan]
    
    # Check voucher availability
    available = await db.voucher_pool.find_one({"plan": plan, "assigned": False})
    if not available:
        raise HTTPException(status_code=400, detail="No voucher codes available for this plan.")
    
    order_id = f"WF-{uuid.uuid4().hex[:10].upper()}"
    
    phone = customer["phone"].strip()
    if phone.startswith('0'):
        phone_intl = '27' + phone[1:]
    elif phone.startswith('+27'):
        phone_intl = phone[1:]
    elif phone.startswith('+'):
        phone_intl = phone[1:]
    else:
        phone_intl = phone
    
    base_url = APP_BASE_URL
    
    plan_labels = {
        "1_day": "1 Day Pass (R10)", "1dev_1week": "1 Device 1 Week (R60)",
        "1dev_2weeks": "1 Device 2 Weeks (R90)", "1dev_3weeks": "1 Device 3 Weeks (R120)",
        "1dev_4weeks": "1 Device 4 Weeks (R150)", "2dev_1week": "2 Devices 1 Week (R90)",
        "2dev_2weeks": "2 Devices 2 Weeks (R135)", "2dev_3weeks": "2 Devices 3 Weeks (R180)",
        "2dev_4weeks": "2 Devices 4 Weeks (R210)", "test": "Test Plan (R10)",
    }
    plan_label = plan_labels.get(plan, plan)
    
    payment_doc = {
        "id": order_id,
        "plan": plan,
        "amount": amount,
        "customer_name": customer["name"],
        "customer_phone": customer["phone"],
        "customer_email": "",
        "portal_customer_id": user["customer_id"],
        "status": "pending",
        "voucher_code": None,
        "pf_payment_id": None,
        "payment_type": "purchase",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payments.insert_one(payment_doc)
    
    form_data = {
        "merchant_id": PAYFAST_MERCHANT_ID,
        "merchant_key": PAYFAST_MERCHANT_KEY,
        "return_url": f"{base_url}/portal/payment/success?order_id={order_id}",
        "cancel_url": f"{base_url}/portal/payment/cancel",
        "notify_url": f"{base_url}/api/payment/notify",
        "name_first": customer["name"].split()[0] if customer["name"] else "Customer",
        "email_address": "customer@wifi.co.za",
        "cell_number": phone_intl,
        "m_payment_id": order_id,
        "amount": f"{amount:.2f}",
        "item_name": f"WiFi Plan - {plan_label}",
        "item_description": f"WiFi Hotspot {plan_label}",
        "custom_str1": order_id,
        "custom_str2": plan,
    }
    
    signature = generate_payfast_signature(form_data)
    form_data["signature"] = signature
    
    return {"order_id": order_id, "payfast_url": f"{PAYFAST_URL}/eng/process", "form_fields": form_data}

@api_router.get("/portal/referral")
async def portal_referral(user: dict = Depends(verify_portal_token)):
    """Portal: Get referral info"""
    customer = await db.portal_customers.find_one({"id": user["customer_id"]}, {"_id": 0, "password_hash": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    referrals = await db.portal_customers.find(
        {"referred_by": user["customer_id"]},
        {"_id": 0, "name": 1, "created_at": 1}
    ).to_list(100)
    
    base_url = APP_BASE_URL
    
    return {
        "referral_code": customer.get("referral_code", ""),
        "referral_link": f"{base_url}/portal/register?ref={customer.get('referral_code', '')}",
        "total_referrals": len(referrals),
        "points_per_referral": REFERRAL_BONUS_POINTS,
        "referrals": referrals
    }

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

@app.on_event("startup")
async def seed_admin():
    """Seed default admin account on startup if it doesn't exist"""
    admin_email = "b.e.motloung@gmail.com"
    existing = await db.admins.find_one({"email": admin_email})
    if not existing:
        admin_doc = {
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "password": hash_password("Bobla@920821"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.admins.insert_one(admin_doc)
        logger.info(f"Default admin account created: {admin_email}")
    else:
        logger.info(f"Admin account already exists: {admin_email}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
