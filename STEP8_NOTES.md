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

## API docs cleanup
- `/api/docs/` and `/api/schema/` now generate with 0 warnings and 0 errors (was 292 and 592). A test keeps it that way.
- Swagger files are served locally (drf-spectacular-sidecar), so the page works without internet.
- Title/branding is DineX; Swagger examples use real demo logins; "Authorize" accepts the JWT access token.
- Dev SECRET_KEY lengthened (no JWT key-length warning); deal lists are ordered (no pagination warning).
- Demo logins: see `dinex/docs/api_access.md` (run `python manage.py migrate` then `python manage.py seed_demo --reset` first).

## Desktop POS grid and responsive fixes
- POS menu shows 3 dishes per row on a 1280 px laptop and 4 on 1366 px and wider (was 2). Phones and tablets keep 2.
- Fixed header overflow on small phones (360–390 px), cards pushed off-screen by long text, billing account-number overflow.
- `qa_e2e/resp.js` checks 17 pages at 8 screen sizes (360 px to 1920 px) for sideways scrolling and overlapping cards.
- POS cards: the - 0 + control was removed; a small number badge on the photo shows the quantity (change quantity in the cart).

## SEO / Google indexing + developer setup (final)
- Public server-rendered landing page at `/` (one H1, features, pricing 2,999/4,999/6,999, FAQ, CTA), JSON-LD (Organization, WebSite, SoftwareApplication offers in PKR, FAQPage). Terms/agree flow moved to `/start`; `/plans` and `/signup` redirect there. Signed-in users are redirected from `/` to their dashboard.
- Landing page redesigned: dark hero with browser-framed screenshots, WhatsApp demo button (`NEXT_PUBLIC_WHATSAPP`, default founder number), numbers strip, alternating feature sections, 3-step band, pricing, FAQ, final CTA.
- `robots.txt`, `sitemap.xml` (`/`, `/terms`), 1200x630 Open Graph + Twitter image, canonical links, per-page titles, noindex (meta + X-Robots-Tag) for login/signup/app/admin/API. Caddy adds `X-Robots-Tag: noindex` to `/api`, `/django-admin`, `/static`.
- Env: `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_CONTACT_PHONE`, `NEXT_PUBLIC_CONTACT_EMAIL`, `NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION` (Dockerfile ARGs, compose build args, `deploy/setup.sh`). Search Console steps are in `deploy/README.md`.
- Dev-ready: root `README.md`, `Makefile`, `scripts/dev-setup|dev|test` (.sh and .bat), `.env.example` files, `.gitignore`, `.editorconfig`. Verified from a clean copy: setup, both servers up, docs/landing/robots return 200.
- Fix: `seed_demo` could crash with "Counted cash cannot be negative" (random shortage on a small drawer); counted cash is now clamped at 0.
- QA: backend 408+ tests OK; E2E steps 1,2,4-9 pass; new `step10.js` (SEO, 24 checks) and `resp_public.js` (4 public pages x 8 screen sizes) pass.
- Billing renewal notice: the next monthly invoice is issued `BILLING_RENEWAL_NOTICE_DAYS` (default 4) days before the period ends, due on the renewal day; the restaurant sees a banner with the amount and date, pays, sends the transaction ID/proof, and the admin approves. Unpaid after the due date + 7 days grace -> suspended (read-only).
- Landing/PDF screenshots now come from the `seed_demo` restaurant (Karachi Grill) with real dish photos (`demo_images/`) and an open shift.
