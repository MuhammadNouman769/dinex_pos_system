# DineX — Step 2 (offline POS, deals, images)
- POS sends one `POST /orders/sync/` per order. If the network is down, the order is saved in IndexedDB (outbox) with a temporary `OFF-MMDD-NNN` number and synced automatically (duplicate-safe via client_uuid).
- Offline payment: cash/card/wallet/bank saved with the order (needs an open shift when online last checked).
- Service worker caches the app shell + images; menu/tables cached for offline reload. You must have logged in once on the device.
- Menu → tap a dish picture to upload/take a photo (compressed to ≤1000px); Deals & combos manager under Setup → Menu.
- Orders page shows "waiting to sync" strip; top-bar sync pill lets you retry/print/discard.
- QA: backend 321 tests OK; `next build` OK; Playwright E2E (online order, deal discount, offline x2 + payment, reload offline, sync exactly once) OK.
- Step 3 (next): mobile/tablet app-feel polish, new PWA icons, payroll QA, final zip.
