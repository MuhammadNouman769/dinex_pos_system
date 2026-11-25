# Step 1 — Terms → Plans → Signup → 14-day trial → Pay → Admin approves

## Flow
1. `/` Terms of Use (scroll + agree) → `/plans` 3 plan cards → `/signup?plan=…` → restaurant + owner created, **14-day trial starts**, owner is signed in and lands on `/setup`.
2. When the trial ends the app shows a paywall (data stays safe, read-only). Owner opens **Billing**, sends money to a JazzCash/Easypaisa/bank account shown there, enters the TID (+ optional screenshot).
3. XverLabs admin opens **Admin → Payments**, checks the money, presses **Approve & activate** (or Reject with a reason). The restaurant switches on immediately.
4. Admin → Payments also manages the payment accounts restaurants see.

## New API
- `GET  /api/v1/public/plans/` · `POST /api/v1/public/signup/` (throttled: `SIGNUP_RATE`, default 10/hour per IP)
- `GET  /api/v1/platform/billing/me/` (now also plans, payment accounts, submissions)
- `POST /api/v1/platform/billing/me/payments/` (JSON or multipart) · `POST .../select-plan/`
- `GET  /api/v1/platform/payments/?status=PENDING` · `POST .../payments/<id>/approve|reject/`
- `GET/POST /api/v1/platform/payment-accounts/` · `PATCH/DELETE .../<id>/`
- `POST /api/v1/orders/sync/` (one-shot, idempotent order placement; used by Step 2 offline mode)

## Also in this step
- New design system (fonts self-hosted, cardamom/saffron palette, new UI kit).
- Next.js upgraded to a patched 15.1.x.
- Terms text is in `dinex-web/src/lib/terms.ts` — **have a lawyer review it** and bump `TERMS_VERSION` (also `TERMS_VERSION` env on the backend) when it changes.
- Tests: 316 backend tests pass (`python manage.py test tests`).

## Run locally
```
cd dinex && cp .env.example .env && pip install -r requirements.txt && python manage.py migrate && python manage.py createsuperuser && python manage.py runserver
cd dinex-web && echo NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 > .env.local && npm ci && npm run dev
```
Then add a JazzCash/bank account in Admin → Payments so restaurants know where to pay.
