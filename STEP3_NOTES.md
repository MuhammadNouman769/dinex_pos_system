# DineX — Step 3 (mobile / tablet app feel + new menu cards)
- New POS MenuCard: big photo, price under the name, round + button, quantity stepper on the card, deal ribbon ("Save PKR X") and struck-through price.
- Phones & tablets (< 1024px): bottom tab bar (Home, POS, Orders, Cash + More sheet with the rest and Sign out). Desktop keeps the sidebar.
- Tablet POS: menu + order panel side by side. Phone: floating "View order" bar + bottom sheet.
- Safe-area insets (notch / home bar), no tap highlight, no pull-to-refresh bounce, 16px inputs (no iOS zoom), standalone-mode polish.
- PWA: new green icons (192/512/maskable/apple), manifest shortcuts (New order, Orders). Install via browser "Add to Home screen".
- Payroll daily wages: verified (53 payroll tests incl. daily-wage cases) and payroll page checked on desktop/tablet/phone.
- QA: backend 321 tests OK, next build OK, Playwright E2E Step 1 (terms → plans → signup → trial → paywall → payment → approve) and Step 2 (online/offline orders, sync, images, deals) both pass.
