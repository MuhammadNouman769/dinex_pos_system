# Step 8 — Loyalty points, email codes, forgot password

**Loyalty (per restaurant, Setup → Restaurant → Loyalty points)**
- Owner sets: spend per 1 point, value of 1 point, minimum points to use (default 100), email-customers and weekly-reminder switches. A live example shows points per 1,000 and the % given back.
- Points are earned when a bill is fully paid (on the total after discount). Using points = a discount on the bill; refunds take back earned points and return used points.
- Points cannot be used below the minimum (server enforces it).
- Cashier types customer phone (+ optional email) at the POS; known customers show their balance. Customers are per branch.
- The printed bill shows points earned / used / balance plus a two-line plain-English description.
- Customers page (nav → Customers): search, points, orders, spent, CSV.

**Email codes**
- Forgot password (login page link): 6-digit code by email, 10 min, 5 tries, resend gap, generic answer (no account enumeration).
- My account → Email: add or change the email; the code goes to the new address; the current password is required.
- Customers get a points email after each paid bill (if they gave an email and the switch is on).
- Reminders 1–2 times a week: cron `0 11 * * 1,4  python manage.py send_loyalty_reminders` or the "Send reminders now" button.

**Real emails** need SMTP env vars (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, DEFAULT_FROM_EMAIL). Without them codes are printed in the server log (dev).

QA: 408 backend tests OK; E2E steps 1/2/4/5/6/7/8 pass.

## Deployment additions
- `deploy/setup.sh` now writes the `EMAIL_*` (SMTP) settings into `.env` — fill them before going live.
- `deploy/docker-compose.yml` has a `reminders` container (daily `send_loyalty_reminders`; each customer at most every 3 days).
- E2E step 9 covers the POS UI: new customer with email, returning customer sees points, "Use points" in the pay modal.
