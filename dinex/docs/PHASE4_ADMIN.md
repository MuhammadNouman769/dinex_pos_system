# DineX – Phase 4: DineX Admin, subscriptions, invoices (+ demo data)

Run tests: `python manage.py test tests`  (127 tests)

## Who is who
- **XverLabs staff** = users with `role = PLATFORM` (`python manage.py createsuperuser` makes one). They use `/admin` in the web app and the `/api/v1/platform/…` API.
- **Restaurants** = organizations. Each has a **Subscription** (plan + status) and **Invoices**.

## Subscription life cycle
`TRIAL` (14 days, set by `BILLING_TRIAL_DAYS`) → admin clicks **Start billing** → `ACTIVE` (first invoice issued) →
unpaid after the due date → `PAST_DUE` (warning banner, still works) → `SUSPENDED` after the grace period (`BILLING_GRACE_DAYS`, default 7).
Admin can also suspend / cancel / reactivate by hand. Marking the overdue invoice **paid** reactivates automatically.

**Suspended, cancelled or expired-trial = read-only:** the restaurant can still sign in and look at everything, but any change returns HTTP 402 with the reason. XverLabs staff are never blocked. Restaurants with no subscription row (created before billing existed) are never blocked.

**Plan limits:** branches and staff accounts per plan; going over returns 402 ("ask XverLabs to upgrade"). A plan can't be lowered below current usage.

## Daily job (cron)
```
python manage.py run_billing      # once a day
```
Issues the next invoice when a paid period ends, marks overdue invoices (PAST_DUE), suspends after the grace period. Safe to run repeatedly.

## Admin API (`/api/v1/platform/`, platform staff only)
| Endpoint | Purpose |
|---|---|
| `GET overview/` | Restaurants by status, MRR, collected this month, overdue, trials ending, orders & sales processed (30d) |
| `GET/POST restaurants/`, `GET/PATCH restaurants/<id>/` | List (search, `status=`), **create restaurant** (owner + first branch + plan + trial days, optional `activate`), detail with usage / users / invoices / activity, enable-disable account |
| `POST restaurants/<id>/subscription/` `{action}` | `activate`, `change_plan`, `extend_trial`, `suspend`, `reactivate`, `cancel`, `set_price`, `note` |
| `POST restaurants/<id>/reset-password/` | Support: set the owner's password |
| `POST restaurants/<id>/invoices/` | Manual invoice |
| `GET invoices/` (`status=DUE|OVERDUE|PAID|VOID`, `search=`), `POST invoices/<id>/pay/`, `…/void/` | Invoices |
| `GET/POST plans/`, `PATCH plans/<id>/` | Plans (starter 2,999 · growth 4,999 · pro 6,999 are created by a migration) |
| `GET billing/me/` | The restaurant owner's own plan, usage and invoices |

`/auth/me/` now includes `subscription` (status, days left, blocked, message) for the banner.

## Web app (DineX Admin, `/admin`)
Overview · Restaurants (search, filters, add) · Restaurant detail (actions, usage vs plan, people, invoices, activity) · Invoices (mark paid) · Plans (edit).
Owners get **Billing** in their own menu and a banner when the trial is ending / payment is overdue / the account is read-only.

## Demo data
`python manage.py seed_demo --reset` — see `docs/DEMO_DATA.md`.

## Known limits
- Payments from restaurants to XverLabs are recorded by hand (bank, JazzCash, Easypaisa…). No online gateway yet.
- No email/WhatsApp reminders yet: `run_billing` only changes statuses.
