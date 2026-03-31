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

# ManyChat API Configuration (must be after load_dotenv)
MANYCHAT_API_KEY = os.environ.get('MANYCHAT_API_KEY', '')
MANYCHAT_BASE_URL = "https://api.manychat.com"

# PayFast Configuration
PAYFAST_MERCHANT_ID = os.environ.get('PAYFAST_MERCHANT_ID', '')
PAYFAST_MERCHANT_KEY = os.environ.get('PAYFAST_MERCHANT_KEY', '')
PAYFAST_PASSPHRASE = os.environ.get('PAYFAST_PASSPHRASE', '')
PAYFAST_SANDBOX_MODE = os.environ.get('PAYFAST_SANDBOX_MODE', 'false').lower() == 'true'
PAYFAST_URL = "https://sandbox.payfast.co.za" if PAYFAST_SANDBOX_MODE else "https://www.payfast.co.za"

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

# ==================== MANYCHAT FUNCTIONS ====================

async def send_manychat_message(phone_number: str, message: str, channel: str = "whatsapp") -> dict:
    """Send message via ManyChat API"""
    if not MANYCHAT_API_KEY:
        logger.error("ManyChat API key not configured")
        return {"success": False, "error": "ManyChat API key not configured"}
    
    headers = {
        "Authorization": f"Bearer {MANYCHAT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as http_client:
            subscriber_id = await get_or_create_manychat_subscriber(http_client, headers, phone_number)
            
            if not subscriber_id:
                return {"success": False, "error": "Could not create subscriber"}
            
            # Build content based on channel
            content_type = "whatsapp" if channel == "whatsapp" else "sms"
            payload = {
                "subscriber_id": subscriber_id,
                "data": {
                    "version": "v2",
                    "content": {
                        "type": content_type,
                        "messages": [
                            {
                                "type": "text",
                                "text": message
                            }
                        ]
                    }
                }
            }
            
            response = await http_client.post(
                f"{MANYCHAT_BASE_URL}/fb/sending/sendContent",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                resp_data = response.json()
                if resp_data.get("status") == "success":
                    return {"success": True, "data": resp_data}
                else:
                    logger.error(f"ManyChat API returned error: {resp_data}")
                    return {"success": False, "error": resp_data.get("message", "Unknown ManyChat error")}
            else:
                logger.error(f"ManyChat send error: {response.status_code} - {response.text}")
                return {"success": False, "error": f"ManyChat HTTP {response.status_code}: {response.text[:200]}"}
                
    except Exception as e:
        logger.error(f"ManyChat API error: {str(e)}")
        return {"success": False, "error": str(e)}

async def get_or_create_manychat_subscriber(client: httpx.AsyncClient, headers: dict, phone_number: str) -> Optional[int]:
    """Get existing subscriber or create new one in ManyChat"""
    try:
        # Clean phone number - ensure it has country code
        clean_phone = phone_number.strip()
        if not clean_phone.startswith('+'):
            if clean_phone.startswith('0'):
                clean_phone = '+27' + clean_phone[1:]
            else:
                clean_phone = '+' + clean_phone
        
        # Try to find subscriber by WhatsApp phone
        find_response = await client.get(
            f"{MANYCHAT_BASE_URL}/fb/subscriber/findBySystemField",
            params={"field": "whatsapp_phone", "value": clean_phone},
            headers=headers,
            timeout=10.0
        )
        
        if find_response.status_code == 200:
            data = find_response.json()
            if data.get("status") == "success" and data.get("data"):
                subscriber_id = data["data"].get("id")
                if subscriber_id:
                    return subscriber_id
        
        # Try phone field
        find_phone_response = await client.get(
            f"{MANYCHAT_BASE_URL}/fb/subscriber/findBySystemField",
            params={"field": "phone", "value": clean_phone},
            headers=headers,
            timeout=10.0
        )
        
        if find_phone_response.status_code == 200:
            data = find_phone_response.json()
            if data.get("status") == "success" and data.get("data"):
                subscriber_id = data["data"].get("id")
                if subscriber_id:
                    return subscriber_id
        
        # Create new subscriber with consent_phrase (required by ManyChat)
        create_payload = {
            "phone": clean_phone,
            "whatsapp_phone": clean_phone,
            "consent_phrase": "I agree",
            "has_opt_in_sms": True,
            "has_opt_in_email": True
        }
        
        create_response = await client.post(
            f"{MANYCHAT_BASE_URL}/fb/subscriber/createSubscriber",
            json=create_payload,
            headers=headers,
            timeout=10.0
        )
        
        if create_response.status_code == 200:
            data = create_response.json()
            if data.get("status") == "success" and data.get("data"):
                subscriber_id = data["data"].get("id")
                if subscriber_id:
                    return subscriber_id
        
        logger.error(f"Failed to create subscriber: {create_response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error in get_or_create_subscriber: {str(e)}")
        return None

async def send_payment_reminder_manychat(customer_name: str, phone: str, amount: float, voucher_code: str, channel: str = "whatsapp") -> dict:
    """Send payment reminder via ManyChat"""
    message = f"Hi {customer_name}, this is a friendly reminder that your WiFi subscription of R{amount:.2f} is due on the last day of this month. Your voucher code: {voucher_code}. Please make payment to avoid service interruption. Thank you!"
    
    return await send_manychat_message(phone, message, channel)

async def send_voucher_code_manychat(customer_name: str, phone: str, voucher_code: str, plan: str, channel: str = "whatsapp") -> dict:
    """Send voucher code via ManyChat"""
    plan_text = "3 devices (R200)" if plan == "3_devices" else "4 devices (R300)"
    message = f"Hi {customer_name}, here is your WiFi voucher code: {voucher_code}\n\nPlan: {plan_text}\n\nEnjoy your internet! Contact us if you need any assistance."
    
    return await send_manychat_message(phone, message, channel)

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

# ==================== MANYCHAT MESSAGING ROUTES ====================

class SendReminderRequest(BaseModel):
    customer_id: str
    channel: str = "whatsapp"  # "whatsapp" or "sms"

class SendVoucherRequest(BaseModel):
    customer_id: str
    channel: str = "whatsapp"

class BulkReminderRequest(BaseModel):
    channel: str = "whatsapp"

@api_router.post("/messaging/send-reminder")
async def send_single_reminder(data: SendReminderRequest, email: str = Depends(verify_token)):
    """Send payment reminder to a single customer via ManyChat"""
    customer = await db.customers.find_one({"id": data.customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    result = await send_payment_reminder_manychat(
        customer["name"],
        customer["phone"],
        get_monthly_rate(customer.get("plan", "3_devices")),
        customer["voucher_code"],
        data.channel
    )
    
    # Log the message regardless of success/failure
    log_doc = {
        "id": str(uuid.uuid4()),
        "customer_id": customer["id"],
        "customer_name": customer["name"],
        "customer_phone": customer["phone"],
        "message_type": "payment_reminder",
        "channel": data.channel,
        "status": "sent" if result.get("success") else "failed",
        "error": result.get("error") if not result.get("success") else None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.message_logs.insert_one(log_doc)
    
    if result.get("success"):
        return {"message": f"Reminder sent to {customer['name']} via {data.channel}", "success": True}
    else:
        error_msg = result.get("error", "Failed to send message")
        raise HTTPException(status_code=400, detail=f"ManyChat: {error_msg}")

@api_router.post("/messaging/send-voucher")
async def send_voucher_to_customer(data: SendVoucherRequest, email: str = Depends(verify_token)):
    """Send voucher code to a customer via ManyChat"""
    customer = await db.customers.find_one({"id": data.customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    result = await send_voucher_code_manychat(
        customer["name"],
        customer["phone"],
        customer["voucher_code"],
        customer.get("plan", "3_devices"),
        data.channel
    )
    
    # Log the message regardless of success/failure
    log_doc = {
        "id": str(uuid.uuid4()),
        "customer_id": customer["id"],
        "customer_name": customer["name"],
        "customer_phone": customer["phone"],
        "message_type": "voucher_code",
        "channel": data.channel,
        "status": "sent" if result.get("success") else "failed",
        "error": result.get("error") if not result.get("success") else None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.message_logs.insert_one(log_doc)
    
    if result.get("success"):
        return {"message": f"Voucher sent to {customer['name']} via {data.channel}", "success": True}
    else:
        error_msg = result.get("error", "Failed to send message")
        raise HTTPException(status_code=400, detail=f"ManyChat: {error_msg}")

@api_router.post("/messaging/send-bulk-reminders")
async def send_bulk_reminders(data: BulkReminderRequest, email: str = Depends(verify_token)):
    """Send payment reminders to all active customers via ManyChat"""
    customers = await db.customers.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    sent_count = 0
    failed_count = 0
    results = []
    
    for customer in customers:
        result = await send_payment_reminder_manychat(
            customer["name"],
            customer["phone"],
            get_monthly_rate(customer.get("plan", "3_devices")),
            customer["voucher_code"],
            data.channel
        )
        
        # Log each message
        log_doc = {
            "id": str(uuid.uuid4()),
            "customer_id": customer["id"],
            "customer_name": customer["name"],
            "customer_phone": customer["phone"],
            "message_type": "payment_reminder",
            "channel": data.channel,
            "status": "sent" if result.get("success") else "failed",
            "error": result.get("error"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.message_logs.insert_one(log_doc)
        
        if result.get("success"):
            sent_count += 1
        else:
            failed_count += 1
            results.append({"customer": customer["name"], "error": result.get("error")})
    
    return {
        "message": f"Sent {sent_count} reminders, {failed_count} failed",
        "sent": sent_count,
        "failed": failed_count,
        "errors": results[:10]  # Return first 10 errors
    }

@api_router.get("/messaging/logs")
async def get_message_logs(email: str = Depends(verify_token)):
    """Get message delivery logs"""
    logs = await db.message_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return logs

@api_router.get("/messaging/status")
async def get_messaging_status(email: str = Depends(verify_token)):
    """Check ManyChat configuration status"""
    is_configured = bool(MANYCHAT_API_KEY)
    return {
        "manychat_configured": is_configured,
        "api_key_set": is_configured,
        "channels_available": ["whatsapp", "sms"] if is_configured else []
    }

# ==================== VOUCHER POOL MANAGEMENT (ADMIN) ====================

class VoucherPoolEntry(BaseModel):
    code: str
    plan: str  # "3_devices" or "4_devices"

class VoucherBulkAdd(BaseModel):
    codes: List[str]
    plan: str

@api_router.post("/vouchers/add")
async def add_voucher_codes(data: VoucherBulkAdd, email: str = Depends(verify_token)):
    """Admin: Add voucher codes to the pool"""
    if data.plan not in PLAN_RATES:
        raise HTTPException(status_code=400, detail="Plan must be '3_devices' or '4_devices'")
    
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
            "assigned": False,
            "assigned_to": None,
            "assigned_at": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        added += 1
    
    return {"message": f"Added {added} voucher codes ({duplicates} duplicates skipped)", "added": added, "duplicates": duplicates}

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
    plan: str  # "3_devices" or "4_devices"
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None

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
    available = await db.voucher_pool.find_one({"plan": data.plan, "assigned": False})
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
    
    base_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://reminder-blast-1.preview.emergentagent.com')
    
    payment_doc = {
        "id": order_id,
        "plan": data.plan,
        "amount": amount,
        "customer_name": data.customer_name,
        "customer_phone": data.customer_phone,
        "customer_email": data.customer_email or "",
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
            voucher = await db.voucher_pool.find_one_and_update(
                {"plan": plan, "assigned": False},
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
            
            # Try to send voucher via ManyChat
            if MANYCHAT_API_KEY and payment.get("customer_phone"):
                try:
                    await send_voucher_code_manychat(
                        payment["customer_name"],
                        payment["customer_phone"],
                        voucher_code,
                        plan,
                        "whatsapp"
                    )
                    logger.info(f"Voucher sent via ManyChat to {payment['customer_phone']}")
                except Exception as mc_err:
                    logger.error(f"ManyChat send failed: {mc_err}")
            
            logger.info(f"Payment {order_id} completed. Voucher: {voucher_code}")
        
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
