# DineX Step 7: final gaps
- Kitchen display (/kitchen): live New / Cooking / Ready columns, minutes timer (amber 10, red 20), options and notes, one-tap advance, new-order beep (mutable), full screen. Phone friendly.
- My account (avatar in the top bar): change password (current password required, strength rules, rate-limited), sign out. API: POST /auth/change-password/.
- CSV export: orders, expenses, end-of-day. Excel-safe (UTF-8 BOM), spreadsheet formulas in notes neutralised.
- Floor plan: drag tables to place them (Step 6 follow-up), Auto-arrange to reset.
- Tests: 381 backend, E2E steps 1, 2, 4, 5, 6, 7 pass.
