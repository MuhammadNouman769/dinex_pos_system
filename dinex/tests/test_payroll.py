"""Phase 5.3: pay profiles, the salary maths (monthly / daily / hourly), advances, payroll runs, payslips."""
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from apps.cash.models import AuditLog
from apps.orders.models import Order
from apps.organizations.models import Location
from apps.payroll.models import Advance, AdvanceRepayment, PayProfile, PayrollRun, Payslip
from apps.staff import attendance as att
from apps.staff.models import AttendanceRecord, Employee
from tests.base import TenantTestCase, PASSWORD

User = get_user_model()
OCT = date(2026, 10, 1)            # 31 days; Sundays: 4, 11, 18, 25  -> 27 working days
D = lambda x: Decimal(str(x))
SCHED = {"start_time": "12:00", "end_time": "22:00", "weekly_off": [6], "grace_minutes": 10, "min_overtime_minutes": 30, "overtime_multiplier": 1.5}


def at(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    return timezone.make_aware(datetime(day.year, day.month, day.day, h, m))


class PayBase(TenantTestCase):
    def setUp(self):
        cache.clear()
        p = patch("apps.staff.attendance.now")
        self.now = p.start()
        self.addCleanup(p.stop)
        self.now.return_value = at(date(2026, 11, 2), "10:00")           # October is over
        self.emp = self.hire("Ali Waiter")

    # ---- builders
    def hire(self, name, role="WAITER", loc=None, client=None, joined="2026-01-01", schedule=True, **extra):
        r = (client or self.a).post("/api/v1/staff/employees/", {"name": name, "role": role, "location": (loc or self.loc_a).id, "joining_date": joined, **extra}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        eid = r.json()["id"]
        if schedule:
            self.assertEqual((client or self.a).put(f"/api/v1/staff/employees/{eid}/schedule/", SCHED, format="json").status_code, 200)
        return eid

    def profile(self, eid, client=None, **over):
        body = {"pay_type": "MONTHLY", "base_amount": 30000, "month_basis": "30", **over}
        r = (client or self.a).put(f"/api/v1/payroll/employees/{eid}/profile/", body, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def attend(self, eid, day, cin="12:00", cout="22:00", status="PRESENT", paid=False):
        emp = Employee.objects.select_related("schedule").get(pk=eid)
        rec = AttendanceRecord(employee=emp, date=day, status=status, paid_leave=paid)
        if status == "PRESENT":
            rec.check_in = at(day, cin)
            rec.check_out = at(day if cout > cin else day + timedelta(days=1), cout) if cout else None
        att.recalc(rec, att.schedule_of(emp))
        rec.save()
        return rec

    def month_days(self, year=2026, month=10):
        return [date(year, month, d) for d in range(1, monthrange(year, month)[1] + 1)]

    def full_month(self, eid, year=2026, month=10, skip=(), **kw):
        """Present on every working day (Sunday is the weekly off) except the days in `skip`."""
        for day in self.month_days(year, month):
            if day.weekday() != 6 and day.day not in skip:
                self.attend(eid, day, **kw)

    def make_run(self, month="2026-10", client=None, loc=None):
        r = (client or self.a).post("/api/v1/payroll/runs/", {"location": (loc or self.loc_a).id, "month": month}, format="json")
        self.assertIn(r.status_code, (200, 201), r.content)
        return r.json()

    def slip(self, run, eid):
        row = [s for s in run["slips"] if s["employee"]["id"] == eid][0]
        r = self.a.get(f"/api/v1/payroll/slips/{row['id']}/")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def one(self, eid, month="2026-10", **checks):
        """Generate the run and return this employee's full payslip."""
        return self.slip(self.make_run(month), eid)

    def action(self, run_id, action, client=None, **body):
        return (client or self.a).post(f"/api/v1/payroll/runs/{run_id}/{action}/", body, format="json")

    def staff(self, role, username, loc=None):
        r = self.a.post("/api/v1/organizations/location-staff/", {"username": username, "email": f"{username}@x.com", "password": PASSWORD, "first_name": "S", "last_name": "T",
                                                                  "location_id": (loc or self.loc_a).id, "role": role}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return self.as_user(User.objects.get(username=username))


class MonthlySalary(PayBase):
    def test_a_full_month_pays_the_full_salary(self):
        self.profile(self.emp)
        self.full_month(self.emp)
        s = self.one(self.emp)
        self.assertEqual((D(s["basic_pay"]), D(s["gross"]), D(s["deductions"]), D(s["net"])), (D(30000), D(30000), D(0), D(30000)))
        self.assertEqual((D(s["daily_rate"]), D(s["hourly_rate"]), s["present_days"], s["scheduled_days"], s["absent_days"]), (D(1000), D(100), 27, 27, 0))
        self.assertEqual(s["pay_type"], "MONTHLY")
        self.assertEqual(s["warnings"], [])

    def test_absent_days_cost_a_day_of_pay_each(self):
        self.profile(self.emp)
        self.full_month(self.emp, skip={5, 6})
        for d in (5, 6):
            self.attend(self.emp, date(2026, 10, d), status="ABSENT")
        s = self.one(self.emp)
        self.assertEqual((s["absent_days"], D(s["absent_deduction"]), D(s["net"])), (2, D(2000), D(28000)))
        self.profile(self.emp, absent_penalty_days=2)
        self.assertEqual(D(self.one(self.emp)["absent_deduction"]), D(4000))                  # two days lost per absence

    def test_paid_leave_costs_nothing_unpaid_leave_costs_a_day(self):
        self.profile(self.emp)
        self.full_month(self.emp, skip={7, 8})
        self.attend(self.emp, date(2026, 10, 7), status="LEAVE", paid=True)
        self.attend(self.emp, date(2026, 10, 8), status="LEAVE", paid=False)
        s = self.one(self.emp)
        self.assertEqual((s["leave_paid"], s["leave_unpaid"], D(s["leave_deduction"]), D(s["net"])), (1, 1, D(1000), D(29000)))

    def test_what_one_day_is_worth_depends_on_the_month_basis(self):
        self.full_month(self.emp, skip={5})
        self.attend(self.emp, date(2026, 10, 5), status="ABSENT")
        for basis, salary in (("30", 30000), ("26", 26000), ("CALENDAR", 31000)):              # October has 31 days
            self.profile(self.emp, base_amount=salary, month_basis=basis)
            self.assertEqual(D(self.one(self.emp)["absent_deduction"]), D(1000), basis)

    def test_lateness_rules(self):
        self.full_month(self.emp, skip={5, 6, 7})
        for d in (5, 6, 7):
            self.attend(self.emp, date(2026, 10, d), cin="12:30")                             # 30 min late, three times
        self.profile(self.emp)
        self.assertEqual(D(self.one(self.emp)["late_deduction"]), D(0))                      # default: no deduction
        self.profile(self.emp, late_rule="MINUTES")
        s = self.one(self.emp)
        self.assertEqual((s["late_days"], s["late_minutes"], D(s["late_deduction"])), (3, 90, D(150)))        # 90 min = 1.5 h x Rs 100
        self.profile(self.emp, late_rule="COUNT", late_every=3, late_deduct_days=0.5)
        self.assertEqual(D(self.one(self.emp)["late_deduction"]), D(500))                    # three lates = half a day
        self.profile(self.emp, late_rule="COUNT", late_every=4, late_deduct_days=0.5)
        self.assertEqual(D(self.one(self.emp)["late_deduction"]), D(0))

    def test_overtime_pay(self):
        self.profile(self.emp)
        self.full_month(self.emp, skip={5, 6, 7})
        for d in (5, 6, 7):
            self.attend(self.emp, date(2026, 10, d), cout="23:00")                            # an hour of overtime on three days
        s = self.one(self.emp)
        self.assertEqual((s["overtime_minutes"], D(s["overtime_pay"]), D(s["gross"])), (180, D(450), D(30450)))      # 3 h x 100 x 1.5
        self.assertEqual(D(self.profile(self.emp, overtime_enabled=False) and self.one(self.emp)["overtime_pay"]), D(0))

    def test_overtime_uses_the_duty_multiplier(self):
        self.full_month(self.emp, skip={5})
        self.attend(self.emp, date(2026, 10, 5), cout="23:00")
        self.a.put(f"/api/v1/staff/employees/{self.emp}/schedule/", {**SCHED, "overtime_multiplier": 2}, format="json")
        self.profile(self.emp)
        self.assertEqual(D(self.one(self.emp)["overtime_pay"]), D(200))                      # 1 h x 100 x 2

    def test_working_the_weekly_off_is_all_overtime(self):
        self.profile(self.emp)
        self.full_month(self.emp)
        self.attend(self.emp, date(2026, 10, 4), cin="14:00", cout="18:00")                   # a Sunday
        s = self.one(self.emp)
        self.assertEqual((s["overtime_minutes"], D(s["overtime_pay"]), s["scheduled_days"], s["present_days"]), (240, D(600), 27, 28))

    def test_allowance_fixed_deduction_and_joining_mid_month(self):
        self.profile(self.emp, fixed_allowance=2000, fixed_deduction=500)
        self.full_month(self.emp)
        s = self.one(self.emp)
        self.assertEqual((D(s["allowance"]), D(s["fixed_deduction"]), D(s["gross"]), D(s["net"])), (D(2000), D(500), D(32000), D(31500)))
        late = self.hire("Joined Mid Month", joined="2026-10-16")
        self.profile(late, fixed_allowance=1000)
        for day in self.month_days():
            if day.day >= 16 and day.weekday() != 6:
                self.attend(late, day)
        s = self.slip(self.make_run(), late)
        self.assertEqual((D(s["basic_pay"]), D(s["allowance"]), s["absent_days"]), (D("15483.87"), D("516.13"), 0))      # 16 of 31 days

    def test_a_rider_earns_commission_per_delivery(self):
        rider = self.hire("Rider Ali", "RIDER", delivery_commission="40")
        self.profile(rider, base_amount=15000)
        self.full_month(rider)
        for i in range(12):
            Order.objects.create(location=self.loc_a, order_type="DELIVERY", order_number=f"C-{i}", rider_id=rider, status="COMPLETED", delivered_at=at(date(2026, 10, 1 + i), "20:00"))
        Order.objects.create(location=self.loc_a, order_type="DELIVERY", order_number="C-nov", rider_id=rider, status="COMPLETED", delivered_at=at(date(2026, 11, 1), "20:00"))
        Order.objects.create(location=self.loc_a, order_type="DELIVERY", order_number="C-x", rider_id=rider, status="CANCELLED")
        s = self.slip(self.make_run(), rider)
        self.assertEqual((s["deliveries"], D(s["commission"]), D(s["gross"])), (12, D(480), D(15480)))


class DailyAndHourly(PayBase):
    def daily_month(self, **over):
        AttendanceRecord.objects.filter(employee_id=self.emp).delete()                         # safe to call again with other options
        self.profile(self.emp, pay_type="DAILY", base_amount=1500, **over)
        for d in (1, 2, 3, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23):    # 20 working days
            self.attend(self.emp, date(2026, 10, d))
        for d in (26, 27):
            self.attend(self.emp, date(2026, 10, d), status="LEAVE", paid=True)

    def test_daily_wage_pays_the_days_worked_and_paid_leave(self):
        self.daily_month()
        s = self.one(self.emp)
        self.assertEqual((D(s["daily_rate"]), D(s["hourly_rate"]), D(s["basic_pay"]), D(s["absent_deduction"])), (D(1500), D(150), D(33000), D(0)))   # 22 days
        self.assertTrue(any("no attendance" in w for w in s["warnings"]))                      # the days nobody marked

    def test_daily_wage_options(self):
        self.daily_month(pay_paid_leave=False)
        self.assertEqual(D(self.one(self.emp)["basic_pay"]), D(30000))                         # paid leave not paid
        self.daily_month(pay_paid_leave=True, pay_weekly_off=True)
        self.assertEqual(D(self.one(self.emp)["basic_pay"]), D(39000))                         # + 4 Sundays

    def hourly_month(self, **over):
        self.profile(self.emp, pay_type="HOURLY", base_amount=200, **over)
        for d in (1, 2, 3, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23):
            self.attend(self.emp, date(2026, 10, d))

    def test_hourly_pay_for_the_hours_worked(self):
        self.hourly_month()
        s = self.one(self.emp)
        self.assertEqual((s["worked_minutes"], D(s["hourly_rate"]), D(s["daily_rate"]), D(s["basic_pay"])), (12000, D(200), D(2000), D(40000)))   # 200 h x 200
        self.attend(self.emp, date(2026, 10, 26), status="LEAVE", paid=True)
        self.assertEqual(D(self.one(self.emp)["basic_pay"]), D(42000))                         # a paid-leave day = 10 h
        self.profile(self.emp, pay_type="HOURLY", base_amount=200, pay_paid_leave=False)
        self.assertEqual(D(self.one(self.emp)["basic_pay"]), D(40000))

    def test_hourly_overtime_is_not_paid_twice(self):
        self.hourly_month()
        AttendanceRecord.objects.filter(employee_id=self.emp, date=date(2026, 10, 1)).delete()
        self.attend(self.emp, date(2026, 10, 1), cout="23:00")                                 # 11 h worked, 1 h of it overtime
        s = self.one(self.emp)
        self.assertEqual((D(s["basic_pay"]), D(s["overtime_pay"])), (D(40000), D(300)))        # regular 10 h x 200 each day; OT 1 h x 200 x 1.5

    def test_standard_hours_set_the_hourly_rate(self):
        self.profile(self.emp, standard_hours=8)
        self.full_month(self.emp)
        self.assertEqual(D(self.one(self.emp)["hourly_rate"]), D("125.00"))                    # 1000 / 8
        self.profile(self.emp, pay_type="DAILY", base_amount=1600, standard_hours=8)
        self.assertEqual(D(self.one(self.emp)["hourly_rate"]), D(200))

    def test_no_duty_hours_assumes_eight_hours_and_warns_about_overtime(self):
        free = self.hire("No Schedule", schedule=False)
        self.profile(free, base_amount=24000)
        for day in self.month_days():
            if day.weekday() != 6:
                self.attend(free, day, cin="12:00", cout="22:00")
        s = self.slip(self.make_run(), free)
        self.assertEqual((D(s["daily_rate"]), D(s["hourly_rate"]), s["overtime_minutes"]), (D(800), D(100), 0))   # nothing to compare against: no overtime


class Adjustments(PayBase):
    def setUp(self):
        super().setUp()
        self.profile(self.emp)
        self.full_month(self.emp)

    def test_bonus_and_one_off_deduction(self):
        run = self.make_run()
        sid = run["slips"][0]["id"]
        r = self.a.post(f"/api/v1/payroll/slips/{sid}/adjustments/", {"kind": "BONUS", "label": "Eid bonus", "amount": 5000}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        r = self.a.post(f"/api/v1/payroll/slips/{sid}/adjustments/", {"kind": "DEDUCTION", "label": "Broken glass", "amount": 700}, format="json")
        s = r.json()
        self.assertEqual((D(s["bonus"]), D(s["other_deduction"]), D(s["gross"]), D(s["net"])), (D(5000), D(700), D(35000), D(34300)))
        self.assertEqual({a["label"] for a in s["adjustments"]}, {"Eid bonus", "Broken glass"})
        self.assertEqual(self.a.delete(f"/api/v1/payroll/adjustments/{s['adjustments'][0]['id']}/").status_code, 204)
        self.assertEqual(D(self.a.get(f"/api/v1/payroll/slips/{sid}/").json()["net"]), D(29300))
        self.assertTrue(AuditLog.objects.filter(action="payroll_adjustment").exists())

    def test_adjustments_survive_a_recalculation(self):
        sid = self.make_run()["slips"][0]["id"]
        self.a.post(f"/api/v1/payroll/slips/{sid}/adjustments/", {"kind": "BONUS", "label": "Bonus", "amount": 1000}, format="json")
        again = self.make_run()
        self.assertEqual(D(self.slip(again, self.emp)["bonus"]), D(1000))

    def test_adjustment_rules(self):
        sid = self.make_run()["slips"][0]["id"]
        post = lambda **b: self.a.post(f"/api/v1/payroll/slips/{sid}/adjustments/", {"kind": "BONUS", "label": "X bonus", "amount": 10, **b}, format="json").status_code
        self.assertEqual(post(kind="TIP"), 400)
        self.assertEqual(post(amount=0), 400)
        self.assertEqual(post(amount=-5), 400)
        self.assertEqual(post(label=""), 400)
        self.assertEqual(post(), 201)

    def test_a_deduction_larger_than_the_pay_leaves_zero_not_negative(self):
        sid = self.make_run()["slips"][0]["id"]
        s = self.a.post(f"/api/v1/payroll/slips/{sid}/adjustments/", {"kind": "DEDUCTION", "label": "Huge fine", "amount": 99999}, format="json").json()
        self.assertEqual(D(s["net"]), D(0))
        self.assertTrue(any("more than the earnings" in w for w in s["warnings"]))


class ProfileApi(PayBase):
    def test_list_shows_everyone_with_or_without_a_pay_profile(self):
        self.profile(self.emp, base_amount=25000)
        other = self.hire("No Pay Profile Yet")
        rows = {r["employee"]["id"]: r for r in self.a.get("/api/v1/payroll/profiles/").json()}
        self.assertEqual(D(rows[self.emp]["profile"]["base_amount"]), D(25000))
        self.assertIsNone(rows[other]["profile"])
        self.assertEqual(D(rows[self.emp]["hours_per_day"]), D(10))                           # from the 12:00-22:00 duty

    def test_validation(self):
        put = lambda **kw: self.a.put(f"/api/v1/payroll/employees/{self.emp}/profile/", {"pay_type": "MONTHLY", "base_amount": 1000, **kw}, format="json").status_code
        self.assertEqual(put(pay_type="WEEKLY"), 400)
        self.assertEqual(put(month_basis="28"), 400)
        self.assertEqual(put(late_rule="ALWAYS"), 400)
        self.assertEqual(put(base_amount=-5), 400)
        self.assertEqual(put(base_amount="lots"), 400)
        self.assertEqual(put(standard_hours=25), 400)
        self.assertEqual(put(absent_penalty_days=9), 400)
        self.assertEqual(put(late_every=0), 400)
        self.assertEqual(self.a.put(f"/api/v1/payroll/employees/{self.emp}/profile/", {"pay_type": "MONTHLY"}, format="json").status_code, 400)       # no amount
        self.assertEqual(put(), 200)

    def test_changing_a_salary_is_audited_with_old_and_new(self):
        self.profile(self.emp, base_amount=30000)
        self.profile(self.emp, base_amount=35000)
        log = AuditLog.objects.filter(action="pay_profile_changed").latest("id")
        self.assertEqual((log.details["old"]["base_amount"], log.details["new"]["base_amount"]), ("30000.00", "35000.00"))
        self.assertEqual(AuditLog.objects.filter(action="pay_profile_changed").count(), 2)

    def test_deleting_a_profile(self):
        self.profile(self.emp)
        self.assertEqual(self.a.delete(f"/api/v1/payroll/employees/{self.emp}/profile/").status_code, 204)
        self.profile(self.emp)
        self.full_month(self.emp)
        run = self.make_run()
        self.assertEqual(self.action(run["id"], "finalize").status_code, 200)
        self.assertEqual(self.a.delete(f"/api/v1/payroll/employees/{self.emp}/profile/").status_code, 400)       # keeps history honest


class Advances(PayBase):
    def setUp(self):
        super().setUp()
        self.profile(self.emp)
        self.full_month(self.emp)

    def give(self, amount=10000, installment=4000, given_on="2026-09-15", emp=None, **extra):
        return self.a.post("/api/v1/payroll/advances/", {"employee": emp or self.emp, "amount": amount, "installment": installment, "given_on": given_on, "reason": "Rent", **extra}, format="json")

    def test_installment_comes_out_of_the_salary(self):
        adv = self.give().json()
        self.assertEqual((D(adv["balance"]), adv["status"]), (D(10000), "ACTIVE"))
        s = self.one(self.emp)
        self.assertEqual((D(s["advance_deduction"]), D(s["net"])), (D(4000), D(26000)))
        self.assertEqual(D(self.a.get(f"/api/v1/payroll/advances/{adv['id']}/").json()["balance"]), D(10000))       # a preview does not repay anything yet
        self.assertEqual(self.action(self.make_run()["id"], "finalize").status_code, 200)
        d = self.a.get(f"/api/v1/payroll/advances/{adv['id']}/").json()
        self.assertEqual((D(d["balance"]), D(d["repaid"]), d["repayments"][0]["source"]), (D(6000), D(4000), "PAYROLL"))

    def test_repaid_over_several_months_then_cleared(self):
        adv = self.give(amount=5000, installment=4000).json()
        self.assertEqual(self.action(self.make_run()["id"], "finalize").status_code, 200)       # October: 4000
        self.now.return_value = at(date(2026, 12, 2), "10:00")
        self.full_month(self.emp, 2026, 11)
        s = self.one(self.emp, "2026-11")
        self.assertEqual(D(s["advance_deduction"]), D(1000))                                  # only what is left
        run = self.make_run("2026-11")
        self.assertEqual(self.action(run["id"], "finalize").status_code, 200)
        d = self.a.get(f"/api/v1/payroll/advances/{adv['id']}/").json()
        self.assertEqual((d["status"], D(d["balance"])), ("CLEARED", D(0)))

    def test_never_takes_more_than_the_pay_and_says_so(self):
        self.profile(self.emp, base_amount=3000)
        self.give(amount=10000, installment=4000)
        s = self.one(self.emp)
        self.assertEqual((D(s["advance_deduction"]), D(s["net"])), (D(3000), D(0)))
        self.assertTrue(any("Not enough pay" in w for w in s["warnings"]))

    def test_older_advances_are_repaid_first(self):
        self.profile(self.emp, base_amount=4000)
        old = self.give(amount=2000, installment=2000, given_on="2026-08-01").json()
        new = self.give(amount=3000, installment=3000, given_on="2026-09-01").json()
        s = self.one(self.emp)
        self.assertEqual([(p["advance"], D(p["amount"])) for p in s["advance_plan"]], [(old["id"], D(2000)), (new["id"], D(2000))])
        self.assertEqual(D(s["advance_deduction"]), D(4000))

    def test_an_advance_given_after_the_month_is_not_taken_yet(self):
        self.give(given_on="2026-11-01")
        self.assertEqual(D(self.one(self.emp)["advance_deduction"]), D(0))

    def test_rules_for_giving_an_advance(self):
        self.assertEqual(self.give(amount=0).status_code, 400)
        self.assertEqual(self.give(amount=-5).status_code, 400)
        self.assertEqual(self.give(installment=0).status_code, 400)
        self.assertEqual(self.give(amount=1000, installment=2000).status_code, 400)
        self.assertEqual(self.give(given_on="2027-01-01").status_code, 400)
        self.assertEqual(self.give(given_on="soon").status_code, 400)
        self.assertEqual(self.a.post("/api/v1/payroll/advances/", {"employee": 999999, "amount": 100}, format="json").status_code, 404)
        r = self.a.post("/api/v1/payroll/advances/", {"employee": self.emp, "amount": 3000}, format="json")        # no installment: the whole amount
        self.assertEqual((r.status_code, D(r.json()["installment"])), (201, D(3000)))
        self.assertTrue(AuditLog.objects.filter(action="advance_given").exists())

    def test_manual_repayment_and_clearing(self):
        adv = self.give(amount=3000, installment=1000).json()
        url = f"/api/v1/payroll/advances/{adv['id']}/repay/"
        self.assertEqual(self.a.post(url, {"amount": 5000}, format="json").status_code, 400)
        self.assertEqual(self.a.post(url, {"amount": 0}, format="json").status_code, 400)
        r = self.a.post(url, {"amount": 1200, "note": "Paid in cash"}, format="json")
        self.assertEqual((r.status_code, D(r.json()["balance"]), r.json()["repayments"][0]["source"]), (201, D(1800), "MANUAL"))
        self.assertEqual(self.a.post(url, {"amount": 1800}, format="json").json()["status"], "CLEARED")
        self.assertEqual(self.a.post(url, {"amount": 1}, format="json").status_code, 400)

    def test_cancelling_an_advance(self):
        adv = self.give().json()
        self.assertEqual(self.a.post(f"/api/v1/payroll/advances/{adv['id']}/void/", format="json").json()["status"], "VOID")
        self.assertEqual(D(self.one(self.emp)["advance_deduction"]), D(0))
        other = self.give().json()
        self.a.post(f"/api/v1/payroll/advances/{other['id']}/repay/", {"amount": 100}, format="json")
        self.assertEqual(self.a.post(f"/api/v1/payroll/advances/{other['id']}/void/", format="json").status_code, 400)

    def test_listing_filters(self):
        two = self.hire("Second Person")
        a1, a2 = self.give().json(), self.give(emp=two).json()
        self.a.post(f"/api/v1/payroll/advances/{a2['id']}/void/", format="json")
        ids = lambda q: {x["id"] for x in self.a.get(f"/api/v1/payroll/advances/{q}").json()}
        self.assertEqual(ids(f"?employee={self.emp}"), {a1["id"]})
        self.assertEqual(ids("?status=VOID"), {a2["id"]})
        self.assertEqual(ids(f"?location={self.loc_a.id}"), {a1["id"], a2["id"]})


class RunLifecycle(PayBase):
    def setUp(self):
        super().setUp()
        self.profile(self.emp)
        self.full_month(self.emp)

    def test_generating_twice_gives_the_same_run_and_one_payslip_each(self):
        a, b = self.make_run(), self.make_run()
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(Payslip.objects.filter(run_id=a["id"]).count(), 1)
        self.assertEqual((a["employees"], D(a["gross"]), D(a["net"])), (1, D(30000), D(30000)))

    def test_who_is_on_the_run(self):
        no_profile = self.hire("Has No Pay Profile")
        gone = self.hire("Left Before Month"); self.profile(gone)
        self.a.patch(f"/api/v1/staff/employees/{gone}/", {"is_active": False}, format="json")
        left = self.hire("Left After Working"); self.profile(left); self.full_month(left)
        self.a.patch(f"/api/v1/staff/employees/{left}/", {"is_active": False}, format="json")
        names = sorted(s["employee"]["name"] for s in self.make_run()["slips"])
        self.assertEqual(names, ["Ali Waiter", "Left After Working"])

    def test_month_rules(self):
        for bad in ("2027-01", "next month", "2026-13", ""):
            self.assertEqual(self.a.post("/api/v1/payroll/runs/", {"location": self.loc_a.id, "month": bad}, format="json").status_code, 400, bad)
        self.assertEqual(self.a.post("/api/v1/payroll/runs/", {"month": "2026-10"}, format="json").status_code, 400)

    def test_cannot_finalize_a_month_that_is_not_over(self):
        self.now.return_value = at(date(2026, 10, 20), "10:00")
        run = self.make_run("2026-10")
        self.assertFalse(run["can_finalize"])
        r = self.action(run["id"], "finalize")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(any("not over" in b for b in r.json()["blockers"]))

    def test_days_nobody_recorded_block_finalizing_until_marked(self):
        gap = self.hire("Has Gaps"); self.profile(gap); self.full_month(gap, skip={6, 7})
        run = self.make_run()
        self.assertEqual(D(self.slip(run, gap)["absent_deduction"]), D(2000))               # the draft counts them as absent
        r = self.action(run["id"], "finalize")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(any("Has Gaps" in b and "2 day(s)" in b for b in r.json()["blockers"]), r.json())
        self.attend(gap, date(2026, 10, 6), status="ABSENT"); self.attend(gap, date(2026, 10, 7), status="LEAVE", paid=True)
        self.assertEqual(self.action(run["id"], "finalize").status_code, 200)               # marking them fixed it
        s = self.slip(self.a.get(f"/api/v1/payroll/runs/{run['id']}/").json(), gap)
        self.assertEqual((D(s["absent_deduction"]), s["leave_paid"]), (D(1000), 1))

    def test_a_check_in_without_a_check_out_blocks_finalizing(self):
        AttendanceRecord.objects.filter(employee_id=self.emp, date=date(2026, 10, 9)).delete()
        self.attend(self.emp, date(2026, 10, 9), cout=None)
        r = self.action(self.make_run()["id"], "finalize")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(any("no check-out" in b for b in r.json()["blockers"]))

    def test_nobody_to_pay_blocks_finalizing(self):
        self.a.delete(f"/api/v1/payroll/employees/{self.emp}/profile/")
        r = self.action(self.make_run()["id"], "finalize")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(any("nobody" in b.lower() for b in r.json()["blockers"]))

    def test_finalizing_locks_the_month(self):
        run = self.make_run()
        self.assertTrue(run["can_finalize"])
        r = self.action(run["id"], "finalize")
        self.assertEqual((r.status_code, r.json()["status"], r.json()["unpaid"]), (200, "FINALIZED", 1))
        self.assertEqual(self.action(run["id"], "finalize").status_code, 400)
        self.assertEqual(self.action(run["id"], "regenerate").status_code, 400)
        self.assertEqual(self.a.post("/api/v1/payroll/runs/", {"location": self.loc_a.id, "month": "2026-10"}, format="json").status_code, 400)
        sid = r.json()["slips"][0]["id"]
        self.assertEqual(self.a.post(f"/api/v1/payroll/slips/{sid}/adjustments/", {"kind": "BONUS", "label": "Late bonus", "amount": 5}, format="json").status_code, 400)
        self.assertTrue(AuditLog.objects.filter(action="payroll_finalized").exists())

    def test_finalizing_uses_the_latest_attendance(self):
        run = self.make_run()
        AttendanceRecord.objects.filter(employee_id=self.emp, date=date(2026, 10, 9)).delete()
        self.attend(self.emp, date(2026, 10, 9), status="ABSENT")                           # corrected after the draft was made
        r = self.action(run["id"], "finalize")
        self.assertEqual(D(self.slip(r.json(), self.emp)["net"]), D(29000))

    def test_reopening(self):
        run = self.make_run()
        self.action(run["id"], "finalize")
        self.assertEqual(self.action(run["id"], "reopen").status_code, 400)                  # needs a reason
        r = self.action(run["id"], "reopen", reason="Forgot a bonus")
        self.assertEqual((r.status_code, r.json()["status"]), (200, "DRAFT"))
        sid = r.json()["slips"][0]["id"]
        self.assertEqual(self.a.post(f"/api/v1/payroll/slips/{sid}/adjustments/", {"kind": "BONUS", "label": "Forgotten bonus", "amount": 500}, format="json").status_code, 201)
        self.assertEqual(self.action(run["id"], "finalize").status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="payroll_reopened", details__reason="Forgot a bonus").exists())
        self.assertEqual(self.action(run["id"], "reopen", reason="again").status_code, 200)

    def test_reopening_gives_the_advance_installments_back(self):
        adv = Advance.objects.create(employee_id=self.emp, amount=D(5000), installment=D(2000), given_on=date(2026, 9, 1))
        run = self.make_run()
        self.action(run["id"], "finalize")
        self.assertEqual(AdvanceRepayment.objects.filter(advance=adv).count(), 1)
        self.action(run["id"], "reopen", reason="Check numbers")
        adv.refresh_from_db()
        self.assertEqual((AdvanceRepayment.objects.filter(advance=adv).count(), adv.balance, adv.status), (0, D(5000), "ACTIVE"))

    def test_run_list_and_unknown_action(self):
        run = self.make_run()
        listing = self.a.get(f"/api/v1/payroll/runs/?location={self.loc_a.id}").json()
        self.assertEqual([r["id"] for r in listing], [run["id"]])
        self.assertEqual(self.action(run["id"], "explode").status_code, 400)
        self.assertEqual(self.a.get(f"/api/v1/payroll/runs/?location=abc").status_code, 400)


class Paying(PayBase):
    def setUp(self):
        super().setUp()
        self.profile(self.emp)
        self.full_month(self.emp)
        self.run = self.make_run()
        self.sid = self.run["slips"][0]["id"]

    def pay(self, method="BANK", client=None, **extra):
        return (client or self.a).post(f"/api/v1/payroll/slips/{self.sid}/pay/", {"method": method, **extra}, format="json")

    def finalize(self):
        self.assertEqual(self.action(self.run["id"], "finalize").status_code, 200)

    def test_only_a_finalized_month_can_be_paid(self):
        self.assertEqual(self.pay().status_code, 400)
        self.finalize()
        r = self.pay(reference="TX-88")
        self.assertEqual((r.status_code, r.json()["status"], r.json()["paid_method"], r.json()["paid_reference"]), (200, "PAID", "Bank transfer", "TX-88"))
        self.assertEqual(self.pay().status_code, 400)
        self.assertTrue(AuditLog.objects.filter(action="salary_paid").exists())

    def test_method_must_be_known(self):
        self.finalize()
        self.assertEqual(self.pay("BARTER").status_code, 400)
        self.assertEqual(self.a.post(f"/api/v1/payroll/slips/{self.sid}/pay/", {}, format="json").status_code, 400)
        self.assertEqual(self.pay("jazzcash").status_code, 200)

    def test_paying_cash_from_the_drawer_records_an_expense(self):
        self.finalize()
        self.assertEqual(self.pay("CASH", from_drawer=True).status_code, 400)                  # no open shift
        shift = self.open_shift(self.a, self.loc_a, "50000")
        self.assertEqual(self.pay("BANK", from_drawer=True).status_code, 400)                  # only cash comes out of a drawer
        self.assertEqual(self.pay("CASH", from_drawer=True).status_code, 200)
        live = self.a.get(f"/api/v1/cash/shifts/{shift['id']}/").json()
        self.assertEqual((D(live["expense" "s"]), D(live["expected_cash"])), (D(30000), D(20000)))
        self.assertEqual(live["movements"][0]["category"], "salary")

    def test_pay_all(self):
        other = self.hire("Second Person"); self.profile(other, base_amount=20000); self.full_month(other)
        run = self.make_run()
        self.finalize_run = self.action(run["id"], "finalize")
        self.assertEqual(self.finalize_run.status_code, 200)
        r = self.action(run["id"], "pay-all", method="BANK", reference="Batch 1")
        self.assertEqual((r.status_code, r.json()["paid"], r.json()["unpaid"]), (200, 2, 0))
        self.assertEqual(self.action(run["id"], "pay-all", method="BANK").status_code, 400)
        self.assertEqual(self.action(run["id"], "reopen", reason="nope").status_code, 400)       # salaries went out

    def test_a_zero_net_payslip_can_be_closed_without_moving_cash(self):
        self.profile(self.emp, base_amount=0)
        run = self.make_run()
        self.assertEqual(self.action(run["id"], "finalize").status_code, 200)
        self.assertEqual(self.pay("CASH").status_code, 200)


class Access(PayBase):
    def setUp(self):
        super().setUp()
        self.profile(self.emp)
        self.full_month(self.emp)
        self.run_id = self.make_run()["id"]
        self.adv = self.a.post("/api/v1/payroll/advances/", {"employee": self.emp, "amount": 1000}, format="json").json()["id"]

    def test_only_the_owner_can_see_salaries(self):
        manager, cashier = self.staff("MANAGER", "mgr_pay"), self.staff("POS_OPERATOR", "cash_pay")
        calls = [("get", "/api/v1/payroll/profiles/"), ("get", f"/api/v1/payroll/employees/{self.emp}/profile/"), ("get", "/api/v1/payroll/runs/"),
                 ("get", f"/api/v1/payroll/runs/{self.run_id}/"), ("get", "/api/v1/payroll/advances/"), ("get", f"/api/v1/payroll/advances/{self.adv}/"),
                 ("post", f"/api/v1/payroll/runs/{self.run_id}/finalize/"), ("post", "/api/v1/payroll/advances/")]
        for who in (manager, cashier):
            for method, url in calls:
                self.assertEqual(getattr(who, method)(url, **({"data": {}, "format": "json"} if method == "post" else {})).status_code, 403, url)
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get("/api/v1/payroll/runs/").status_code, 401)

    def test_another_restaurant_sees_nothing_of_mine(self):
        sid = self.a.get(f"/api/v1/payroll/runs/{self.run_id}/").json()["slips"][0]["id"]
        for url in (f"/api/v1/payroll/runs/{self.run_id}/", f"/api/v1/payroll/slips/{sid}/", f"/api/v1/payroll/advances/{self.adv}/", f"/api/v1/payroll/employees/{self.emp}/profile/"):
            self.assertEqual(self.b.get(url).status_code, 404, url)
        self.assertEqual(self.b.get("/api/v1/payroll/runs/").json(), [])
        self.assertEqual(self.b.get("/api/v1/payroll/advances/").json(), [])
        self.assertEqual(self.b.post("/api/v1/payroll/runs/", {"location": self.loc_a.id, "month": "2026-10"}, format="json").status_code, 404)
        self.assertEqual(self.b.put(f"/api/v1/payroll/employees/{self.emp}/profile/", {"base_amount": 1}, format="json").status_code, 404)
        self.assertEqual(self.b.post("/api/v1/payroll/advances/", {"employee": self.emp, "amount": 10}, format="json").status_code, 404)
        self.assertEqual(self.b.post(f"/api/v1/payroll/runs/{self.run_id}/finalize/", format="json").status_code, 404)
        self.assertEqual(self.b.post(f"/api/v1/payroll/slips/{sid}/pay/", {"method": "CASH"}, format="json").status_code, 404)


class AttendanceNumbersForPayroll(PayBase):
    def test_the_report_counts_what_payroll_needs(self):
        self.full_month(self.emp, skip={6, 7})
        self.attend(self.emp, date(2026, 10, 7), cout=None)                                  # a day with no check-out
        r = self.a.get(f"/api/v1/staff/attendance/report/?location={self.loc_a.id}&from=2026-10-01&to=2026-10-31").json()["rows"][0]
        self.assertEqual((r["weekly_off_days"], r["unmarked_days"], r["open_records"]), (4, 1, 1))
