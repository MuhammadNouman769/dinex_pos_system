# DineX – Phase 5.1: employees, waiter on orders, riders & delivery cash

Run tests: `python manage.py test tests`  (158 tests)

## Employees (`/api/v1/staff/employees/`)
A person record, **separate from a login**: waiters and riders usually do not log in.
Fields: code (E-001…, per restaurant, never reused), name, role (Manager, Cashier, Waiter, Rider, Chef, Kitchen helper, Other), branch, phone, CNIC (13 digits, stored `12345-1234567-1`), address, emergency contact, joining date, active; riders also have vehicle and `delivery_commission` (used by payroll later). Optional link to a login (owner: `POST employees/<id>/link-user/`).
- Everyone at a branch can **read** the list (the POS needs the waiter list); **owner or branch manager** add / edit / remove.
- Filters: `location`, `role`, `search`, `active=false`. Staff only ever see their own restaurant, and non-owners only their branches.
- Removing is a soft delete (old orders keep the name). Not allowed while the person is on an open order, or (rider) still owes cash.
- Detail returns 30-day stats: waiters → orders, sales, average bill; riders → deliveries, average minutes, cash with rider.

## Orders carry the people
- `waiter` on every order (choose on the POS for dine-in; validated: active, same branch, role waiter/manager/cashier). Printed on the bill.
- `rider` on delivery orders, set with `POST /staff/orders/<id>/assign-rider/ {rider}` (change before dispatch; after dispatch only a manager/owner, audited).
- New timestamps `dispatched_at` (rider left) and `delivered_at`.

## Delivery rules
1. **A rider is required to send an order out** (`OUT_FOR_DELIVERY`).
2. **Cash on delivery:** a delivered order may complete unpaid. The money is then *with the rider* until a cashier settles it. (Takeaway/dine-in still cannot complete unpaid.)
3. Prepaid (card / wallet) delivery orders owe nothing to settle.

## Rider cash settlement
- `GET /staff/riders/` – each rider with on-road count, cash to settle, delivered today / 30 days, average delivery minutes.
- `GET /staff/riders/<id>/ledger/` – unsettled delivered orders + recent settlements.
- `POST /staff/riders/<id>/settle/ {handed, order_ids?, note?}` – needs the cashier's **open shift**. Cash is recorded as CASH payments (reference `RS-<id>`) on the rider's oldest orders first, so it lands in the cashier's drawer. If less than owed is handed over, the shortage stays due on the oldest orders, is stored on the settlement and written to the audit log (`rider_shortage`). You cannot receive more than is owed.

## Demo data
Each branch now has a full team (manager, cashiers, 3–6 waiters, 2–3 riders, chefs, helpers), orders with waiters, delivery orders with riders (30 % prepaid), settlements at shift change (about 1 in 8 a little short), and live today: one delivery on the road, one ready without a rider, riders still holding cash.

## Not yet (next parts)
Attendance & overtime · payroll, advances, payslips · analytics dashboards.
