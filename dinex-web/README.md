# DineX Web (by XverLabs)

Next.js 15 + TypeScript + Tailwind frontend for the DineX backend.

## Run it
1. Start the backend (`dinex/`): `python manage.py migrate && python manage.py runserver 8000`
   - make a platform user: `python manage.py createsuperuser`
   - create a restaurant + owner with `POST /api/v1/onboarding/restaurant/` (as that platform user)
2. In this folder:
   ```
   cp .env.example .env.local      # point NEXT_PUBLIC_API_URL at your API
   npm install
   npm run dev                      # http://localhost:3000
   ```
3. Backend `.env` must allow this origin: `CORS_ALLOWED_ORIGINS=http://localhost:3000`

## Screens
| Route | Who | What |
|---|---|---|
| `/login` | all | Sign in |
| `/dashboard` | all | Today's orders, low stock, setup checklist |
| `/setup` | owner | Wizard: restaurant, floors & tables, menu, ingredients, recipes, opening stock |
| `/pos` | owner, manager, cashier | Touch POS: menu grid, cart, dine-in/takeaway/delivery, send to kitchen, print bill |
| `/orders` | owner, manager, cashier | Kitchen board with status buttons, auto-refresh, reprint bill |
| `/staff` | owner, manager | Team (waiters, riders, chefs…), add/edit, 30-day stats; **Attendance** (day board, report, CSV, duty hours, PINs); **Riders & delivery cash**: who is on the road, cash each rider holds, settle cash |
| `/payroll` | owner only | Monthly payroll (monthly / daily / hourly pay, overtime, deductions, commission, advances, payslips), people's pay set-up, advances |
| `/kiosk` | cashier, manager, owner | PIN attendance kiosk for the entrance tablet: type a PIN to check in / out |
| `/cash` | owner, manager, cashier | Cash desk: open/close shift, expenses, cash in/out, expected cash vs counted, shift history |
| `/reports` | owner, manager | Sales, payment methods, busy hours, best sellers with food cost & profit, cancels, refunds, shift differences, audit log (owner) |
| `/inventory` | all (edit: owner, manager) | Stock, low-stock, purchases/wastage/count, history |

## DineX Admin (XverLabs staff only, role PLATFORM)
| Route | What |
|---|---|
| `/admin` | Platform overview: MRR, restaurants by status, overdue invoices, trials ending |
| `/admin/restaurants` | Search / filter all restaurants, add a new one (owner login is generated) |
| `/admin/restaurants/<id>` | Plan & billing actions (start billing, extend trial, suspend, reactivate, change plan, custom price, reset owner password), usage vs plan, people, invoices, activity |
| `/admin/invoices` | All invoices, mark paid |
| `/admin/plans` | Edit plans, prices, limits |
| `/billing` | (owners) their plan, usage and invoices |

Demo logins: see `dinex/docs/DEMO_DATA.md`.

## Notes
- Light/dark theme (toggle in the top bar); mobile layout uses a bottom tab bar.
- Bills print via the browser (80mm layout). Allow pop-ups for the site.
- Money/units: people type kg / litre / dozen; the API stores g / ml / pcs.
- Payments: cash (with change), card, JazzCash/Easypaisa, bank; split payments; orders can't be completed until paid.
- Not built yet: offline mode, online payment gateway for subscriptions, email/WhatsApp reminders.
