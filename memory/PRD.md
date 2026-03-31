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

## Plans
- 3 Devices: R200/month
- 4 Devices: R300/month
- Test Plan: R10 (for testing)

## Tech Stack
- Frontend: React, Tailwind CSS, shadcn/ui
- Backend: FastAPI, MongoDB, PyJWT
- OCR: pytesseract, pdfplumber
- Messaging: ManyChat API
- Payments: PayFast (live mode)

## What's Been Implemented

### Core Features (All Complete)
- [x] Admin JWT authentication
- [x] Customer CRUD with voucher codes
- [x] Pro-rata calculator for 2026
- [x] Refund calculator (1wk=8d, 2wk=15d, 3wk=22d, 4wk=32d)
- [x] Dashboard with stats
- [x] ManyChat WhatsApp/SMS messaging (send-reminder, send-voucher, bulk, logs)
- [x] Distributor portal with PoP batch upload (OCR/PDF extraction)
- [x] Bank statement parsing + PoP matching + commission calculation (20%)
- [x] **PayFast payment gateway** - public payment page, ITN webhook, voucher assignment
- [x] **Admin voucher pool management** - add/delete codes, stats, payment history
- [x] **Success page shows voucher code after payment** (live tested with R10)
- [x] **3-layer ITN validation** (signature → server → merchant_id)

### Pages
- /login - Admin login
- / - Dashboard
- /customers - Customer management
- /calculator - Pro-rata & refund calculators
- /commissions - Commission tracking
- /vouchers - Voucher pool management (admin)
- /reminders - ManyChat messaging
- /settings - WhatsApp & reminder config
- /pay - Public payment page (customer-facing)
- /payment/success - Voucher display after payment
- /payment/cancel - Payment cancellation
- /distributor/login - Distributor login
- /distributor/dashboard - Distributor PoP uploads

## Prioritized Backlog

### P1 - Pending
- [ ] E2E verify bank statement matching with real Capitec files
- [ ] Handle ManyChat edge cases (invalid phone, rate limits)
- [ ] Automatic scheduled reminders (cron on last day of month)

### P2 - Future
- [ ] Customer payment history tracking
- [ ] Export customers to CSV
- [ ] Monthly revenue reports
- [ ] Remove test plan before going live

### P3 - Nice to Have
- [ ] Customer self-service portal
- [ ] Multiple admin users
- [ ] Dark mode toggle
