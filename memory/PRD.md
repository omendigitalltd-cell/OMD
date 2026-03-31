# WiFi Hotspot Admin System - PRD

## Original Problem Statement
WiFi hotspot business admin system with:
- Customer management, pro-rata/refund calculators
- ManyChat WhatsApp/SMS reminders
- Distributor commission management with PoP upload + bank statement matching
- PayFast payment: customers pay online, get voucher code
- **Customer Portal**: register/login, buy plans, purchase history, loyalty points (1pt/R10), rewards redemption, referral system (5pts bonus)

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
- [x] ManyChat WhatsApp/SMS messaging
- [x] Distributor portal with PoP batch upload (OCR/PDF)
- [x] Bank statement parsing + PoP matching + 20% commission
- [x] Voucher pool management (manual + CSV upload)
- [x] Payment tracking with PayFast

### Customer Portal (`/portal/*`)
- [x] Register (name + phone + password) with optional referral code
- [x] Login (phone + password)
- [x] Dashboard with stats (points, purchases, redeemed, referrals)
- [x] Buy Plan via PayFast (authenticated)
- [x] Purchase History (codes, amounts, dates, type)
- [x] Loyalty Points (1pt per R10 spent, balance + history)
- [x] Rewards Redemption (11 tiers, progress bars, free voucher on redeem)
- [x] Referral System (unique code, share link, 5pts bonus each)
- [x] Payment success/cancel pages within portal

### Public Pages
- [x] `/pay` - Public payment page (plan selection + PayFast)
- [x] `/payment/success` and `/payment/cancel`

## Prioritized Backlog
### P1 - Pending
- [ ] E2E verify bank statement matching with real Capitec files
- [ ] Handle ManyChat edge cases
- [ ] Automatic scheduled reminders (cron on last day of month)

### P2 - Future
- [ ] Customer payment history export (CSV)
- [ ] Monthly revenue reports dashboard
- [ ] Remove test plan before production
