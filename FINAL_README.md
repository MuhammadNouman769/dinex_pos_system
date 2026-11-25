# DineX — final release (Steps 1–8 + deployment)
Read deploy/README.md to go live: ./setup.sh <domain> <email>, fill the EMAIL_* lines in deploy/.env, docker compose up -d --build.

# DineX: subscription restaurant POS (final build)

Backend `dinex/` (Django 5 + DRF + JWT) · Frontend `dinex-web/` (Next 15, PWA). Per-step notes: STEP1..STEP6_NOTES.md.

## Run
Backend:  cd dinex && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py createsuperuser && python manage.py runserver
Frontend: cd dinex-web && npm i && NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run build && npm start
Tests:    cd dinex && python manage.py test tests   (381 tests)

## What is inside
1. Signup -> Terms -> 3 plans -> 14-day trial -> manual payment approval (platform admin).
2. POS: categories, dishes with sizes and photos, deals, dish options (spice/extras, required or optional), per-item kitchen notes,
   dine-in (floor plan table picker) / takeaway / delivery, discounts, tax, partial and equal-split payments, split bill, move table.
3. Offline-first: orders save on the device (IndexedDB), sync later without duplicates, offline bill and kitchen ticket, installable app.
4. Printing: customer bill (restaurant name + black-and-white logo on top, account numbers + QR at the bottom), kitchen ticket (KOT), end-of-day report.
5. Tables: floor plan with shapes (square/round/long/wall), seats shown, drag to place tables, live status.
6. Reservations, expenses, suppliers and purchases (stock in with cost), cash desk shifts, end-of-day (Z) report.
7. Kitchen display screen, change password, CSV export (orders, expenses, end of day).
8. Inventory with recipes and automatic deduction, payroll with daily wages, attendance kiosk, reports.

## Loyalty & email (Step 8)
See STEP8_NOTES.md. Set SMTP env vars for real email; add cron `0 11 * * 1,4 python manage.py send_loyalty_reminders` for weekly reminders. Customers/points are per branch.
