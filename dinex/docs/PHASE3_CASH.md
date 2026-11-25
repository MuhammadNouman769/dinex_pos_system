# DineX – Phase 3: payments, shifts, cash, reports, audit

Run tests: `python manage.py test tests`  (96 tests)

## Rules
- **Money only moves through `Payment` rows** (PAYMENT / REFUND) that belong to an **open shift**. `order.payment_status` is derived (PENDING / PARTIAL / PAID / REFUNDED) and cannot be set by a client.
- **An order cannot be COMPLETED until fully paid.** Items added after payment make it PARTIAL again.
- **Cancel needs a reason**; a paid order must be **refunded first**. Cancelling an order already sent to the kitchen = owner/manager only. Cashiers can cancel unsent orders.
- **Refunds and discounts are owner/manager only** (reason required) and written to the **audit log**.
- Expected cash = opening + cash sales − cash refunds + cash in − cash out − expenses − safe drops. Closing a shift stores counted cash and the **difference**. Only the owner can reopen a closed shift (reason, audited).
- Cashiers see only their own shifts; reports are owner/manager; audit log is owner only.

## API (`/api/v1/cash/`)
| Endpoint | Purpose |
|---|---|
| `GET shifts/current/?location=` | My open shift with live totals (or `null`) |
| `POST shifts/open/` `{location, opening_cash}` | Start shift |
| `POST shifts/<id>/close/` `{counted_cash, note}` | Close, returns expected / counted / difference |
| `POST shifts/<id>/reopen/` `{reason}` | Owner only |
| `POST shifts/<id>/movements/` `{kind: CASH_IN/CASH_OUT/EXPENSE/SAFE_DROP, amount, reason, category}` | Drawer movements |
| `GET shifts/`, `GET shifts/<id>/` | History / one shift's Z-report |
| `GET/POST orders/<id>/payments/` | List / take payment `{method: CASH/CARD/WALLET/BANK, amount?, tendered?, reference?}` (amount defaults to balance) |
| `POST orders/<id>/refund/` `{method, amount, reason}` | Manager/owner |
| `GET reports/sales/?location=&from=&to=` | Sales, methods, by day/hour, top items with food cost & profit, cancels, refunds, cashiers, shift differences |
| `GET audit/?action=` | Audit log (owner) |

Also: order status endpoint now takes `{status, reason}`; `/auth/me/` adds `can_view_reports`.

## Notes / limits
- Profit uses recipes: dishes without a recipe are listed in `items_without_recipe` and profit is overstated until they are added.
- Tax/discount/service in a shift report are summed per paid order (an order paid across two shifts is counted in both).
- Manager approval is role-based (no PIN yet).
