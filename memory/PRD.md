# WiFi Hotspot Admin System - PRD

## Original Problem Statement
WiFi hotspot business admin system with:
- Customer management, pro-rata/refund calculators
- BulkSMS messaging for vouchers and payment reminders
- Distributor commission management with PoP upload + bank statement matching
- PayFast payment: customers pay online, get voucher code
- **Customer Portal**: register/login, buy plans, purchase history, loyalty points (1pt/R10), rewards redemption

## Plans
| Plan | Price | Points Earned |
|------|-------|--------------|
| 1 Day Pass | R10 | 1 pt |
| 1 Device 1 Week | R60 | 6 pts |
| 1 Device 2 Weeks | R90 | 9 pts |
| 1 Device 3 Weeks | R120 | 12 pts |
| 1 Device 4 Weeks | R150 | 15 pts |
| 2 Devices 1 Week | R90 | 9 pts |
| 2 Devices 2 Weeks | R135 | 13 pts |
| 2 Devices 3 Weeks | R180 | 18 pts |
| 2 Devices 4 Weeks | R210 | 21 pts |
| 3 Devices Monthly | R200 | 20 pts |
| 4 Devices Monthly | R300 | 30 pts |

## What's Been Implemented (All Complete)

### Admin System
- [x] JWT auth, customer CRUD, dashboard with stats
- [x] Pro-rata calculator (2026), refund calculator
- [x] BulkSMS messaging (replaced ManyChat) - send vouchers & reminders via SMS
- [x] Distributor portal with PoP batch upload (OCR/PDF)
- [x] Bank statement parsing + PoP matching + 20% commission
- [x] Voucher pool management (manual + CSV + PDF upload with 6-digit regex)
- [x] Payment tracking with PayFast

### Customer Portal (`/portal/*`)
- [x] Register (name + phone + password + accommodation) 
- [x] Login (phone + password)
- [x] Dashboard with stats (points, purchases, redeemed)
- [x] Buy Plan via PayFast (authenticated)
- [x] Purchase History (codes, amounts, dates, type)
- [x] Loyalty Points (1pt per R10 spent, balance + history)
- [x] Rewards Redemption (11 tiers, progress bars, free voucher on redeem)
- [x] Payment success/cancel pages within portal

### Public Pages
- [x] `/pay` - Public payment page (plan selection + PayFast)
- [x] `/payment/success` and `/payment/cancel`

### Messaging (BulkSMS)
- [x] Single SMS reminder to customer
- [x] Single SMS voucher delivery to customer
- [x] Bulk SMS reminders to all active customers
- [x] Post-payment automatic voucher delivery via SMS (PayFast ITN callback)
- [x] Message delivery logs with status tracking

## Prioritized Backlog
### P1 - Next
- [ ] E2E verify bank statement ↔ PoP matching with real Capitec files
- [ ] Automatic scheduled reminders (cron on last day of month)
- [ ] Remove "Test Plan" (R10) before production

### P2 - Future
- [ ] Customer payment history export (CSV)
- [ ] Monthly revenue reports dashboard
- [ ] Update Settings page (replace WhatsApp config with BulkSMS config display)
