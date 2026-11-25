# DineX Step 6: reservations, expenses, suppliers/purchases, end-of-day report

New backend app `apps/operations` (migration 0001), API under `/api/v1/operations/`.

- Reservations: guest, phone, party size, date/time, stay length, table (capacity + overlap checks), notes.
  Actions: seat (table -> occupied), no-show, cancel, complete. Cashiers can book; tenant + branch scoped.
  UI: Reservations page (day navigation), "Bookings" button and booked-time note on Tables.
- Expenses: category chips, amount, note, date. Can be paid from the cash drawer (creates a shift EXPENSE movement, so expected cash drops)
  or outside the till. Drawer expenses cannot be deleted. Owner/manager only.
- Suppliers + Purchases: supplier list with balances; "Receive stock" bill with several lines (kg/g/l/ml/pcs/dozen),
  stocks ingredients in with weighted-average cost, partial payment now, "Pay" later for what is still due.
- End of day (Z report): net sales by method, expenses by category (cash-desk expenses included once), purchases bought/paid/owed,
  net after costs, each cashier's expected/counted/difference, warning for shifts still open, best sellers, bookings summary. Prints on 80mm.
- Tests: 376 backend (21 new), E2E steps 1, 2, 4, 5, 6 pass with no page errors.
