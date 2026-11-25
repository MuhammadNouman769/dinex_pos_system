# DineX – Phase 5.3: payroll (monthly, daily, hourly), advances, payslips

**Owner only.** Salaries are private: managers and cashiers get 403 on every payroll endpoint, and other restaurants get 404.

## Pay profile (one per employee) – `PUT /api/v1/payroll/employees/<id>/profile/`
| Setting | Meaning |
|---|---|
| `pay_type` | `MONTHLY` salary · `DAILY` wage · `HOURLY` rate |
| `base_amount` | the salary, the wage per day, or the rate per hour |
| `month_basis` | monthly only: one day's pay = salary ÷ `30`, `26` or the real days of the month (`CALENDAR`) |
| `standard_hours` | paid hours in a normal day (for the hourly rate). Empty = taken from the duty hours, else 8 |
| `fixed_allowance` / `fixed_deduction` | added / taken every month (food, transport / EOBI, uniform) |
| `overtime_enabled` | pay overtime at the **overtime multiplier set in the employee's duty hours** (default 1.5×) |
| `absent_penalty_days` | monthly: days of pay lost per absent day (default 1) |
| `pay_paid_leave`, `pay_weekly_off` | daily / hourly: are paid-leave days (and, for daily wage, the weekly off) paid? |
| `late_rule` | `NONE` · `MINUTES` (late minutes at the hourly rate) · `COUNT` (every `late_every` late days = `late_deduct_days` days of pay) |
Every change is written to the audit log with the old and new values.

## The maths (`apps/payroll/calc.py`)
- **Monthly:** basic = salary (pro-rated by calendar days if the person joined during the month). Deductions: absent days × penalty × daily rate, unpaid-leave days × daily rate.
- **Daily wage:** basic = wage × (days worked + paid leave [if paid] + weekly offs [if paid]). Days not worked are simply not paid.
- **Hourly:** basic = rate × regular hours (+ paid-leave days × hours per day, if paid).
- **Overtime** (all types) = overtime hours × hourly rate × multiplier. Working a weekly off counts completely as overtime.
- **Rider commission** = delivered orders in the month × the rider's commission per delivery.
- **Bonus / one-off deduction** are added by hand on a draft payslip.
- **Advance installments** come last and never take more than what is left, so net pay is never negative (the rest stays owed, with a warning).
- Hourly rate: monthly = daily ÷ hours; daily = wage ÷ hours; hourly = the rate. Amounts are rounded to the paisa.

## Advances – `POST /payroll/advances/ {employee, amount, installment?, given_on?, reason}`
`installment` is taken from each month's salary (default: all at once). Oldest advance first. Repay directly with `POST advances/<id>/repay/`; cancel with `…/void/` (only before any repayment). Installments are **only recorded when a month is finalized**; a draft is a preview. Reopening a month returns them.

## Monthly run – `POST /payroll/runs/ {location, month: "YYYY-MM"}`
1. **Prepare** (draft): works out everyone with a pay profile from attendance, deliveries and advances. Recalculate any time; bonuses survive.
2. **Finalize** locks the month, takes the advance installments and makes the payslips "to pay". It is **refused** (with the reasons listed) when: the month is not over; anyone has a day with **no attendance recorded** (mark it present / absent / leave); a past day has a check-in but no check-out; or nobody has a pay profile. This is deliberate so nobody's pay is cut by a forgotten click.
3. **Pay**: `slips/<id>/pay/ {method, reference?, from_drawer?}` or `runs/<id>/pay-all/`. Paying cash with `from_drawer` records an expense (category *salary*) on the payer's open shift, so the cash drawer stays right.
4. **Reopen** (`reason` required) only while nobody has been paid.
Salary figures in a payslip are a snapshot: later changes to a profile never rewrite old months.

## Web app
**Payroll** (owner): *Monthly payroll* (prepare, review each payslip with its full breakdown, bonus / deduction, finalize, pay, reopen, print), *People & pay* (set up each person, with a form that adapts to monthly / daily / hourly), *Advances*. Printable A5 payslip.

## Demo data
Pay profiles for everyone (monthly mostly, some daily-wage helpers and waiters, hourly and daily waiters, rider allowance and commission, chef allowance), advances being repaid, **last month finalized** (paid at three branches; unpaid at Karachi DHA so you can try *Pay all* and *Pay from drawer*) and **this month as a live draft** with a couple of bonuses.

## Not included (yet)
Income-tax / EOBI / provident-fund calculations (use *Monthly deduction* or a manual deduction), loans with interest, salary history by effective date (a change applies to the next payroll you prepare), email / WhatsApp payslips, bank-file export.
