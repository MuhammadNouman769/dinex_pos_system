# DineX – Phase 0 (security & correctness) changes

Run tests: `python manage.py test tests`  (37 tests)

## Fixed
- Cross-tenant leaks: orders/customers search+date+stats, PATCH moving rows to another org,
  related FKs (location/customer/table/category/tags/variant) now org-scoped via `OrganizationScopedMixin`.
- Membership `user_id` only for users already in your organization; removed members can be re-added.
- Crashes: `Order.OrderStatus`, `Table.TableStatus` (delete order, stats, available/occupy/free).
- `order_type` was saved as "True" (validator returned True) – fixed.
- `order_number`: per location, local date, no reuse, retry on race.
- Order `status` / `payment_status` / `created_by` are server-only; item price+name come from catalog.
- Discount can't make total negative; totals recalc on discount change; delivery + table auto occupy/free.
- POS: `CanOperatePOS` + `location_scope()` – MANAGER / POS_OPERATOR work only at assigned locations.
- Soft-delete no longer blocks reuse of slug/sku/table number/phone (partial unique constraints).
- Several variants of one product at one location; invalid variants return 400 (no silent drop).
- `createsuperuser` => PLATFORM; password validators; `ALLOWED_HOSTS`; deactivated org is locked out.

## You must do
- **Rotate SECRET_KEY** (old one is in git history) and remove `.env` from git: `git rm --cached .env`.
- Copy `.env.example` to `.env`; set DEBUG=False, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, PostgreSQL in production.
- `python manage.py migrate` (new migrations in accounts, customers, orders, catalog).

## Known gaps (next phases)
- Tax is a fixed 10% (make per-organization), modifiers/deals not used by orders yet.
- Customer stats (`add_order`), payments, shifts, inventory – Phases 2–3.
