# DineX Step 5: dish options, notes, KOT, split bill, table transfer
- POS: dishes with option groups open an options sheet (required/optional, single/multi, extra price, qty, kitchen note). Per-line "Add note" in the cart.
- Prices: options add to unit price; server validates min/max/required (400 on bad choice). Works offline (option ids in the outbox).
- KOT: big qty, options, notes, no prices. Button after ordering and on each Orders card; optional auto-print (POS toggle). Offline orders too.
- Orders: Move table, Split bill (before payment, not deal lines). Options/notes shown on cards.
- Payment: "Split equally between N" in the pay dialog.
- Setup -> Menu -> "+ options" per dish: create group, reuse group, remove.
- Fix: modifier-options API crashed (organization_id); now fixed + test.
- Tests: 355 backend, E2E steps 1/2/4/5 pass.
