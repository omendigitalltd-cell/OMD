# WiFi Hotspot Admin System - PRD

## Original Problem Statement
Create an admin system for WiFi hotspot business where admin can:
- Capture customers by phone numbers and voucher codes
- Send WhatsApp/SMS reminders automatically via ManyChat on last day of month
- Pro-rata calculation feature for each month of 2026
- Refund calculator based on remaining days (custom duration rules)
- Commission management system for distributors (20% commission)
- Distributor PoP upload with OCR/PDF parsing + Bank Statement matching

## User Personas
- **Primary**: WiFi hotspot business owner/admin
- **Secondary**: Distributors who upload proof of payments

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

## Tech Stack
- Frontend: React, Tailwind CSS, shadcn/ui
- Backend: FastAPI, MongoDB, PyJWT
- Auth: JWT tokens
- OCR: pytesseract, pdfplumber
- Messaging: ManyChat API

## What's Been Implemented

### Backend (FastAPI)
- [x] JWT authentication (register/login)
- [x] Customer CRUD with voucher codes
- [x] Pro-rata calculator for all 2026 months
- [x] Refund calculator with custom duration rules
- [x] Dashboard stats API
- [x] ManyChat messaging routes (send-reminder, send-voucher, send-bulk-reminders, logs, status)
- [x] ManyChat subscriber creation with consent_phrase
- [x] Distributor auth (register/login)
- [x] Distributor PoP batch upload with OCR/PDF extraction
- [x] Admin bank statement upload & parsing (Capitec format)
- [x] Proof-to-bank-statement matching logic (partial name match + amount match)
- [x] Commission calculation (20% rate) and payout tracking
- [x] WhatsApp settings configuration
- [x] Reminder scheduling system

### Frontend (React)
- [x] Login/Register page
- [x] Dashboard with stats cards and pro-rata preview
- [x] Customer management (add/edit/delete)
- [x] Pro-rata calculator with visual results
- [x] Refund calculator with twin date selectors
- [x] Messaging page with ManyChat integration (single + bulk sending)
- [x] Settings page (WhatsApp + reminder config)
- [x] Commissions page
- [x] Distributor Login + Dashboard with batch PoP upload

## Known Limitations
- ManyChat subscriber creation requires account-level permissions (user needs to enable API subscriber creation in ManyChat settings or contact ManyChat support)
- Bank statement parsing is optimized for Capitec format
- ManyChat sendContent may not work outside 24h conversation window (WhatsApp Business policy)

## Prioritized Backlog

### P0 - Done
- [x] Admin authentication
- [x] Customer CRUD
- [x] Pro-rata calculator
- [x] Dashboard
- [x] Refund calculator
- [x] ManyChat messaging integration (backend + frontend)
- [x] Distributor portal with PoP upload
- [x] Bank statement matching logic

### P1 - Pending
- [ ] E2E verify bank statement matching with real Capitec files
- [ ] Handle ManyChat edge cases (invalid phone formats, rate limits)
- [ ] Automatic scheduled reminder sending (cron job on last day of month)

### P2 - Future
- [ ] Customer payment history tracking
- [ ] Export customers to CSV
- [ ] Monthly revenue reports
- [ ] ManyChat Flow-based messaging (sendFlow for templates)

### P3 - Nice to Have
- [ ] Customer self-service portal
- [ ] Multiple admin users
- [ ] Dark mode toggle
