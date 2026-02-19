# WiFi Hotspot Admin System - PRD

## Original Problem Statement
Create an admin system for WiFi hotspot business where admin can:
- Capture customers by phone numbers and voucher codes
- Send WhatsApp reminders automatically to remember to pay on last day of month
- Pro-rata calculation feature for each month of 2026

## User Choices
- WhatsApp: Direct WhatsApp Business API
- Customer data: Name only (plus phone, voucher code)
- Plans: R200 (3 devices), R300 (4 devices)

## User Personas
- **Primary**: WiFi hotspot business owner/admin
- Manages customer subscriptions
- Needs simple interface to track payments and send reminders

## Core Requirements (Static)
1. Admin authentication (JWT-based)
2. Customer management (CRUD)
3. Two subscription plans (R200/3 devices, R300/4 devices)
4. Pro-rata calculator for 2026
5. WhatsApp reminder system (configurable)
6. Dashboard with stats

## What's Been Implemented (Feb 19, 2026)

### Backend (FastAPI)
- JWT authentication (register/login)
- Customer CRUD with voucher codes
- Pro-rata calculator for all 2026 months
- Dashboard stats API
- Reminder scheduling system
- WhatsApp settings configuration
- Reminder message template system

### Frontend (React)
- Login/Register page
- Dashboard with stats cards
- Customer management (add/edit/delete)
- Pro-rata calculator with visual results
- Reminders page with test sending
- Settings page (WhatsApp + reminder config)
- Responsive sidebar navigation

## Tech Stack
- Frontend: React, Tailwind CSS, shadcn/ui
- Backend: FastAPI, MongoDB, PyJWT
- Auth: JWT tokens

## Mocked/Pending
- **WhatsApp Business API**: Structure ready, actual API calls pending user credentials

## Prioritized Backlog

### P0 - Critical (Done)
- [x] Admin authentication
- [x] Customer CRUD
- [x] Pro-rata calculator
- [x] Dashboard

### P1 - High Priority
- [ ] Connect WhatsApp Business API (when credentials available)
- [ ] Automatic scheduled reminder sending (cron job)
- [ ] Payment tracking (mark as paid)

### P2 - Medium Priority
- [ ] Customer payment history
- [ ] Bulk SMS/WhatsApp sending
- [ ] Export customers to CSV
- [ ] Monthly revenue reports

### P3 - Nice to Have
- [ ] Customer self-service portal
- [ ] Multiple admin users
- [ ] Dark mode toggle
