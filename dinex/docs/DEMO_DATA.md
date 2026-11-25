# Demo data

```
python manage.py migrate
python manage.py seed_demo --reset        # WIPES the database first, then seeds (~2 min)
python manage.py seed_demo --reset --days 7   # quicker, less history
python manage.py runserver 8000
```
Without `--reset` it refuses to run if demo data exists. Never run `--reset` on a real database.

Everything is created through the real services (orders, stock, payments, shifts), so stock, cash totals and reports are consistent, and history is dated correctly (time is simulated).

## Logins (password `Demo@12345`, except the admin)
| Who | Username | Notes |
|---|---|---|
| **DineX Admin** (XverLabs) | `xverlabs` / `DineX@2026` | Platform panel at `/admin` |
| Owner, Karachi Grill | `karachigrill` | Growth plan, **active**, 2 branches (DHA Phase 6, Clifton), ~4 weeks of history |
| Manager / cashiers, DHA | `karachigrill_dha_mgr`, `karachigrill_dha_c1`, `karachigrill_dha_c2` | Same pattern `karachigrill_clifton_*` for Clifton |
| Owner, Lahore Tikka House | `lahoretikka` | Starter, **active**, 3 weeks |
| Owner, Pizza Corner | `pizzacorner` | Growth, **payment overdue** (warning banner, still works) |
| Owner, Desi Dhaba | `desidhaba` | Starter, **trial ends in ~2 days** |
| Owner, Burger Hub | `burgerhub` | Starter, **brand-new trial, empty**: shows the setup checklist |
| Owner, Cafe Chai Wala | `chaiwala` | Pro, **suspended** for non-payment (read-only, 402 on changes) |

## Attendance kiosk PINs (Staff → Attendance → Open PIN kiosk, or `/kiosk`)
Manager **1111**, day cashier **2222**, evening cashier **3333**; everyone else gets 4001, 4002… per branch. Log in as `karachigrill_dha_c1` on the tablet and type a PIN.

## What is in it
- 6 restaurants, 7 branches, floors & tables (Basement / Ground / First / Rooftop), owners, managers and cashiers.
- Menu of ~24 dishes with sizes, 29 ingredients, 3 in-house preparations (patty, naan dough…), recipes for almost all dishes (Raita and Kheer deliberately have none, so the "no recipe" warning shows).
- 150+ customers with phones/addresses and order counts/spend.
- ~2,500 orders: dine-in / takeaway / delivery, split payments (cash, card, JazzCash/Easypaisa, bank), a few discounts, cancellations with reasons, refunds approved by managers.
- Two shifts a day per branch plus a manager float: expenses, safe drops, and a realistic mix of balanced / short / over drawers (one Rs 500 shortage).
- Every employee has duty hours, a weekly off and a PIN; weeks of attendance (on time, late, left early, overtime, off-day work, absent, paid / unpaid leave, forgotten check-outs).
- **Payroll**: pay profiles for everyone (monthly, daily-wage and hourly), advances being repaid, last month finalized (paid, except Karachi DHA, which is left to pay) and this month as a draft. Owner login → Payroll.
- Daily purchases, stock deducted by sales, a few ingredients left under their reorder level.
- **Live today** at Karachi DHA: orders in every kitchen state (pending, in kitchen, ready-unpaid, ready-paid), occupied tables, an open cashier shift.
- Subscriptions in every state with invoice history (paid, due, overdue).
