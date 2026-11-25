# DineX — Step 4
- POS menu cards: photo, name, price, − qty + (no description text).
- Tables: each table has a shape (4 sides / round / long / 3 sides against wall) and seats. Setup → Floors & tables: pick shape, seats, how many; tap a table to edit/delete.
- New "Tables" page: live floor plan with chairs, colours (green available, red occupied, amber reserved), counts, reserve / cancel reservation / start order.
- POS dine-in: choose table on the floor plan (busy tables greyed out); /pos?table=ID deep link.
- Bill: black-and-white logo + restaurant name on top; account numbers (up to 6) and payment QR (uploaded picture or generated from a link) at the bottom; custom footer line; table number. Setup → Restaurant → "Bill & payment details" (owner only) with "Print a test bill".
- API: GET/PATCH /organizations/me/branding/, POST/DELETE /organizations/me/branding/<logo|qr>/, Table.shape, branding in /auth/me/.
- QA: backend 333 tests OK, next build OK, Playwright E2E steps 1, 2 and 4 pass.
