# WiFi Hotspot Admin System - PRD

## Original Problem Statement
Create an admin system for WiFi hotspot business where admin can:
- Capture customers by phone numbers and voucher codes
- Send WhatsApp/SMS reminders automatically via ManyChat on last day of month
- Pro-rata calculation feature for each month of 2026
- Refund calculator based on remaining days (custom duration rules)
- Commission management system for distributors (20% commission)
- Distributor PoP upload with OCR/PDF parsing + Bank Statement matching
- PayFast payment integration: customers pay online, get voucher code on success page

## User Personas
- **Primary**: WiFi hotspot business owner/admin
- **Secondary**: Distributors who upload proof of payments
- **Tertiary**: Customers who purchase WiFi plans online

## Core Requirements
1. Admin authentication (JWT-based)
2. Customer management (CRUD)
3. Two subscription plans: R200/3 devices, R300/4 devices
4. Pro-rata calculator for 2026
5. Refund calculator (1 week=8d, 2 weeks=15d, 3 weeks=22d, 4 weeks=32d)
6. ManyChat WhatsApp/SMS messaging integration
7. Distributor portal with PoP upload (batch up to 10)
8. Bank statement parsing + PoP matching for commission calculation
9. Dashboard with stats
10. PayFast payment gateway - customer pays, gets voucher code
11. Admin voucher pool management (pre-load codes, track assignments)

## Tech Stack
- Frontend: React, Tailwind CSS, shadcn/ui
- Backend: FastAPI, MongoDB, PyJWT
- Auth: JWT tokens
- OCR: pytesseract, pdfplumber
- Messaging: ManyChat API
- Payments: PayFast (live mode)

## What's Been Implemented

### Backend (FastAPI)
- [x] JWT authentication (register/login)
- [x] Customer CRUD with voucher codes
- [x] Pro-rata calculator for all 2026 months
- [x] Refund calculator with custom duration rules
- [x] Dashboard stats API
- [x] ManyChat messaging routes (send-reminder, send-voucher, send-bulk-reminders, logs, status)
- [x] Distributor auth + PoP batch upload with OCR/PDF extraction
- [x] Bank statement upload & parsing + PoP matching logic
- [x] Commission calculation (20% rate) and payout tracking
- [x] **PayFast payment initiation with MD5 signature generation**
- [x] **PayFast ITN (webhook) callback handler**
- [x] **Voucher pool management (add/list/delete/stats)**
- [x] **Payment verification endpoint**
- [x] **Auto-assign voucher on successful payment + ManyChat notification**

### Frontend (React)
- [x] Login/Register page
- [x] Dashboard with stats cards and pro-rata preview
- [x] Customer management (add/edit/delete)
- [x] Pro-rata calculator with visual results
- [x] Refund calculator with twin date selectors
- [x] Messaging page with ManyChat integration
- [x] Commissions page
- [x] Distributor Login + Dashboard with batch PoP upload
- [x] **Public payment page (/pay) - plan selection + PayFast checkout**
- [x] **Payment success page (/payment/success) - shows voucher code**
- [x] **Payment cancel page (/payment/cancel)**
- [x] **Admin voucher management page (/vouchers) - pool stats, add codes, track assignments**

## Known Limitations
- ManyChat subscriber creation requires account-level permissions
- Bank statement parsing optimized for Capitec format
- PayFast is in LIVE mode (Merchant ID: 31016281)

## Prioritized Backlog

### P0 - Done
- [x] Admin auth, Customer CRUD, Dashboard
- [x] Pro-rata + Refund calculators
- [x] ManyChat messaging integration
- [x] Distributor portal + PoP upload
- [x] Bank statement matching logic
- [x] PayFast payment + voucher assignment
- [x] Admin voucher pool management

### P1 - Pending
- [ ] E2E verify bank statement matching with real Capitec files
- [ ] Handle ManyChat edge cases (invalid phone, rate limits)
- [ ] Automatic scheduled reminders (cron on last day of month)
- [ ] Enable ManyChat subscriber import permissions

### P2 - Future
- [ ] Customer payment history
- [ ] Export customers to CSV
- [ ] Monthly revenue reports
- [ ] ManyChat Flow-based messaging (sendFlow for templates)

### P3 - Nice to Have
- [ ] Customer self-service portal
- [ ] Multiple admin users
- [ ] Dark mode toggle
