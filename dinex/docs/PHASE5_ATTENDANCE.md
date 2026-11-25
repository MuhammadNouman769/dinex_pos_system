# DineX – Phase 5.2: attendance, duty hours and overtime

## Duty hours (`WorkSchedule`, one per employee)
Start and end time, weekly off days (0 = Monday … 6 = Sunday), `grace_minutes` (default 10), `min_overtime_minutes` (default 30) and `overtime_multiplier` (default 1.5, used by payroll next).
`PUT/GET/DELETE /api/v1/staff/employees/<id>/schedule/` · `POST /staff/schedule/bulk/ {location, role?, …}` sets the same hours for a whole group (e.g. all waiters). Owner / branch manager only.
A duty that ends before it starts (16:00 → 01:00) finishes after midnight; the **work day is the date it started**.

## How the numbers are worked out
| | Rule |
|---|---|
| Late | arrived after duty start + grace → minutes since the duty start (12:25 for a 12:00 start = 25) |
| Early leave | left before duty end − grace → minutes before the end |
| Overtime | stayed after the duty end by at least the minimum → minutes after the end (stay 20 min with a 30 min minimum = 0) |
| Weekly off worked | all the time worked is overtime; no late / early |
| No duty hours set | only the time worked is recorded |
| Forgot to check out | closed automatically at the end of duty the next time the person checks in (flagged `auto_closed`) |

## Recording attendance
- **PIN kiosk** (`/kiosk`, entrance tablet logged in as a cashier or manager): the employee types **only their PIN**; the first punch of a day checks in, the next checks out, a third is refused. The screen greets them and shows late / worked / overtime. `POST /staff/attendance/kiosk/ {location, pin}`.
- **Manager**: `POST /staff/attendance/punch/ {employee, action: IN|OUT, time?, note?}`. An entry for an earlier time needs a note and is audited (`attendance_backdated`).
- **Absent / leave**: `POST /staff/attendance/mark/ {employee, date, status: ABSENT|LEAVE, paid, note}`. Leave can be planned for the future; absent cannot.
- **Correction**: `PATCH /staff/attendance/<id>/ {status, check_in, check_out, paid_leave, reason}`. A reason is always required; old and new values go to the audit log (`attendance_edited`, shown in local time). Rows are never deleted.
- Setting a PIN: `POST /staff/employees/<id>/set-pin/ {pin}` (4–6 digits, unique among the branch's active staff; `null` removes it; an empty value is refused so a cleared box can never delete a PIN).

### PIN security
PINs are low-entropy, so they are stored as a fast keyed hash (HMAC-SHA256 with the server `SECRET_KEY` and the employee id) instead of a slow password hash. A slow hash would make the kiosk take seconds (the PIN is checked against everyone at the branch) and protects little against 10^6 guesses. The protection is the **lockout**: 5 wrong PINs lock that branch's tablet for 5 minutes, plus a request rate limit (`KIOSK_RATE`, default 120/min). Never put the database dump and the `SECRET_KEY` in the same place.

## Reading it
- `GET /staff/attendance/?location=&date=` → the **day board**: every active employee with a state: `ON_DUTY, DONE, NOT_IN, UPCOMING, OFF, ABSENT, ABSENT_DERIVED` (no record and the day is over), `LEAVE, NO_SCHEDULE, NOT_JOINED`, plus the record and per-state counts.
- `GET /staff/attendance/report/?location=&from=&to=[&employee=]` → per person: scheduled days, present, late days / minutes, early leaves, absent, paid / unpaid leave, hours worked, overtime minutes, off-days worked, missing check-outs (with day-by-day records for one employee). Range max one year. Today is not counted absent until the duty has ended. The web app exports it to CSV.
- Employee detail now returns `schedule` and `today`.
Board, report, marks and corrections: owner / branch manager. The kiosk: any cashier or manager of the branch. Everything is tenant- and branch-scoped.

## Web app
Staff → **Attendance** (day board with check-in/out, absent/leave and corrections; report with CSV), **Open PIN kiosk**, employee page → *Duty hours* and *Attendance PIN*, and *Duty hours for a group*. Cashiers see an **Attendance** link straight to the kiosk.

## Demo data
Every employee has duty hours, a weekly off and a PIN: **manager 1111, day cashier 2222, evening cashier 3333**, everyone else 4001, 4002… in creation order per branch (look it up in Staff, or set a new one). Weeks of history with late arrivals, early leaves, overtime, off-day work, absences, paid / unpaid leave, a few forgotten check-outs, and one waiter working past midnight.

## Next
Payroll will use these numbers: overtime hours × hourly rate × multiplier, late / absent deductions, rider commissions, advances.
