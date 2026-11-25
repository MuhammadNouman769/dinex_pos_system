"""Phase 5.2: duty hours, attendance (manager + PIN kiosk), late / early / overtime, leave, board, report."""
import time as _time
from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from apps.cash.models import AuditLog
from apps.organizations.models import Location
from apps.staff import attendance as att
from apps.staff.models import AttendanceRecord, Employee
from tests.base import TenantTestCase, PASSWORD

User = get_user_model()
SUN, MON, TUE, WED, THU, FRI = (date(2026, 10, d) for d in (11, 12, 13, 14, 15, 16))      # Oct 15 2026 is a Thursday
SCHED = {"start_time": "12:00", "end_time": "22:00", "weekly_off": [6], "grace_minutes": 10, "min_overtime_minutes": 30, "overtime_multiplier": 1.5}


def at(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    return timezone.make_aware(datetime(day.year, day.month, day.day, h, m))


def iso(day, hhmm):
    return f"{day.isoformat()}T{hhmm}"


class AttBase(TenantTestCase):
    def setUp(self):
        cache.clear()
        p = patch("apps.staff.attendance.now")
        self.now = p.start()
        self.addCleanup(p.stop)
        self.now.return_value = at(THU, "09:00")
        self.emp = self.hire(self.a, "Ali Waiter")
        self.put_schedule(self.emp["id"])

    def hire(self, client, name, role="WAITER", loc=None, **extra):
        r = client.post("/api/v1/staff/employees/", {"name": name, "role": role, "location": (loc or self.loc_a).id, "joining_date": "2026-01-01", **extra}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def put_schedule(self, eid, client=None, **over):
        r = (client or self.a).put(f"/api/v1/staff/employees/{eid}/schedule/", {**SCHED, **over}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def punch(self, action, day, hhmm, eid=None, client=None, **extra):
        # "now" only ever moves forward, so a test controls the clock. Entries for earlier times are late entries,
        # which need a note: the helper always gives one.
        self.now.return_value = max(self.now.return_value, at(day, hhmm) + timedelta(minutes=1))
        extra.setdefault("note", "entered by test")
        return (client or self.a).post("/api/v1/staff/attendance/punch/", {"employee": eid or self.emp["id"], "action": action, "time": iso(day, hhmm), **extra}, format="json")

    def day(self, day, cin, cout, eid=None):
        r1 = self.punch("IN", day, cin, eid); self.assertEqual(r1.status_code, 201, r1.content)
        r2 = self.punch("OUT", day if cout > cin else day + timedelta(days=1), cout, eid); self.assertEqual(r2.status_code, 201, r2.content)
        return r2.json()["record"]

    def staff(self, role, username, loc=None):
        r = self.a.post("/api/v1/organizations/location-staff/", {"username": username, "email": f"{username}@x.com", "password": PASSWORD, "first_name": "S", "last_name": "T",
                                                                  "location_id": (loc or self.loc_a).id, "role": role}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return self.as_user(User.objects.get(username=username))

    def board(self, day=THU, client=None):
        r = (client or self.a).get(f"/api/v1/staff/attendance/?location={self.loc_a.id}&date={day.isoformat()}")
        self.assertEqual(r.status_code, 200, r.content)
        return {row["employee"]["id"]: row for row in r.json()["rows"]}, r.json()


class Metrics(AttBase):
    def test_on_time_full_day(self):
        r = self.day(WED, "11:55", "22:05")
        self.assertEqual((r["late_minutes"], r["early_leave_minutes"], r["overtime_minutes"], r["worked_minutes"]), (0, 0, 0, 610))

    def test_late_only_after_the_grace_period_and_counts_from_duty_start(self):
        self.assertEqual(self.day(MON, "12:10", "22:00")["late_minutes"], 0)                 # exactly at the grace limit
        self.assertEqual(self.day(TUE, "12:11", "22:00")["late_minutes"], 11)
        self.assertEqual(self.day(WED, "12:25", "22:00")["late_minutes"], 25)

    def test_early_leave(self):
        self.assertEqual(self.day(MON, "12:00", "21:00")["early_leave_minutes"], 60)
        self.assertEqual(self.day(TUE, "12:00", "21:52")["early_leave_minutes"], 0)         # inside the grace

    def test_overtime_needs_the_minimum(self):
        self.assertEqual(self.day(MON, "12:00", "22:20")["overtime_minutes"], 0)             # 20 min < 30 minimum
        self.assertEqual(self.day(TUE, "12:00", "22:45")["overtime_minutes"], 45)

    def test_shift_ending_after_midnight_belongs_to_the_day_it_started(self):
        self.put_schedule(self.emp["id"], start_time="16:00", end_time="01:00")
        r = self.day(THU, "16:00", "01:50")
        self.assertEqual((r["date"], r["worked_minutes"], r["overtime_minutes"], r["late_minutes"]), (THU.isoformat(), 590, 50, 0))
        self.assertTrue(self.a.get(f"/api/v1/staff/employees/{self.emp['id']}/schedule/").json()["schedule"]["overnight"])

    def test_working_the_weekly_off_is_all_overtime(self):
        r = self.day(SUN, "14:00", "18:00")
        self.assertEqual((r["on_off_day"], r["overtime_minutes"], r["late_minutes"], r["early_leave_minutes"]), (True, 240, 0, 0))

    def test_without_duty_hours_only_time_worked_is_recorded(self):
        free = self.hire(self.a, "No Schedule")
        r = self.day(WED, "09:00", "23:30", eid=free["id"])
        self.assertEqual((r["worked_minutes"], r["late_minutes"], r["overtime_minutes"], r["early_leave_minutes"]), (870, 0, 0, 0))

    def test_a_forgotten_check_out_is_closed_at_the_end_of_duty_next_time(self):
        self.assertEqual(self.punch("IN", WED, "12:00").status_code, 201)                   # never checked out
        self.now.return_value = at(THU, "12:01")
        r = self.punch("IN", THU, "12:00")
        self.assertEqual(r.status_code, 201, r.content)
        old = AttendanceRecord.objects.get(employee_id=self.emp["id"], date=WED)
        self.assertTrue(old.auto_closed)
        self.assertEqual((timezone.localtime(old.check_out).hour, old.overtime_minutes), (22, 0))
        self.assertEqual(AttendanceRecord.objects.filter(employee_id=self.emp["id"]).count(), 2)


class PunchRules(AttBase):
    def test_in_then_out_and_the_double_clicks(self):
        self.assertEqual(self.punch("IN", THU, "12:00").status_code, 201)
        self.assertEqual(self.punch("IN", THU, "12:05").status_code, 400)                   # already in
        self.assertEqual(self.punch("OUT", THU, "11:00").status_code, 400)                  # before the check-in
        self.assertEqual(self.punch("OUT", THU, "20:00").status_code, 201)
        r = self.punch("IN", THU, "20:30")
        self.assertEqual(r.status_code, 400)
        self.assertIn("already checked in and out", json_text(r))

    def test_out_without_in_and_bad_input(self):
        self.assertEqual(self.punch("OUT", THU, "08:00").status_code, 400)
        self.assertEqual(self.punch("SIDEWAYS", THU, "08:00").status_code, 400)
        r = self.a.post("/api/v1/staff/attendance/punch/", {"employee": self.emp["id"], "action": "IN", "time": "soon"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.a.post("/api/v1/staff/attendance/punch/", {"employee": 999999, "action": "IN"}, format="json").status_code, 404)

    def test_cannot_punch_the_future(self):
        r = self.a.post("/api/v1/staff/attendance/punch/", {"employee": self.emp["id"], "action": "IN", "time": iso(THU, "15:00")}, format="json")   # now = 09:00
        self.assertEqual(r.status_code, 400)
        self.assertIn("future", json_text(r))

    def test_late_entries_need_a_note_and_are_audited(self):
        body = {"employee": self.emp["id"], "action": "IN", "time": iso(WED, "12:00")}
        r = self.a.post("/api/v1/staff/attendance/punch/", body, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("note", r.json())
        r = self.a.post("/api/v1/staff/attendance/punch/", {**body, "note": "Forgot to log"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(AuditLog.objects.filter(action="attendance_backdated", details__note="Forgot to log").exists())
        live = self.a.post("/api/v1/staff/attendance/punch/", {"employee": self.hire(self.a, "Live One")["id"], "action": "IN"}, format="json")   # no time = now: no note needed
        self.assertEqual(live.status_code, 201, live.content)

    def test_absent_or_leave_blocks_punching_until_a_manager_changes_it(self):
        self.a.post("/api/v1/staff/attendance/mark/", {"employee": self.emp["id"], "date": THU.isoformat(), "status": "ABSENT"}, format="json")
        r = self.punch("IN", THU, "12:00")
        self.assertEqual(r.status_code, 400)
        self.assertIn("marked absent", json_text(r))

    def test_inactive_employee_cannot_be_punched(self):
        self.a.patch(f"/api/v1/staff/employees/{self.emp['id']}/", {"is_active": False}, format="json")
        self.assertEqual(self.punch("IN", THU, "12:00").status_code, 400)

    def test_permissions_and_isolation(self):
        cashier = self.staff("POS_OPERATOR", "cash_att")
        self.assertEqual(self.punch("IN", THU, "12:00", client=cashier).status_code, 403)
        self.assertEqual(self.punch("IN", THU, "12:00", client=self.b).status_code, 404)
        manager = self.staff("MANAGER", "mgr_att")
        self.assertEqual(self.punch("IN", THU, "12:00", client=manager).status_code, 201)


def json_text(r):
    import json
    return json.dumps(r.json())


class Kiosk(AttBase):
    def setUp(self):
        super().setUp()
        self.tablet = self.staff("POS_OPERATOR", "tablet")
        self.set_pin(self.emp["id"], "4821")

    def set_pin(self, eid, pin, client=None):
        return (client or self.a).post(f"/api/v1/staff/employees/{eid}/set-pin/", {"pin": pin}, format="json")

    def kiosk(self, pin, client=None, loc=None):
        return (client or self.tablet).post("/api/v1/staff/attendance/kiosk/", {"location": (loc or self.loc_a).id, "pin": pin}, format="json")

    def test_pin_alone_identifies_the_person_and_toggles(self):
        self.now.return_value = at(THU, "12:25")
        r = self.kiosk("4821")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()["action"], r.json()["employee"]["name"], r.json()["late_minutes"]), ("IN", "Ali Waiter", 25))
        self.now.return_value = at(THU, "22:50")
        r = self.kiosk("4821")
        self.assertEqual((r.json()["action"], r.json()["overtime_minutes"], r.json()["worked_minutes"]), ("OUT", 50, 625))
        self.assertEqual(self.kiosk("4821").status_code, 400)                                # a third punch the same day
        self.assertNotIn("4821", json_text(r))

    def test_wrong_pin_then_lockout_then_recovery(self):
        for _ in range(4):
            self.assertEqual(self.kiosk("0000").status_code, 400)
        r = self.kiosk("0000")
        self.assertEqual(r.status_code, 400)
        locked = self.kiosk("4821")                                                          # even the right PIN is refused while locked
        self.assertEqual(locked.status_code, 400)
        self.assertIn("Too many", json_text(locked))
        cache.clear()                                                                         # the lock times out
        self.now.return_value = at(THU, "12:00")
        self.assertEqual(self.kiosk("4821").status_code, 200)

    def test_a_correct_pin_resets_the_failure_count(self):
        for _ in range(3):
            self.kiosk("0000")
        self.now.return_value = at(THU, "12:00")
        self.assertEqual(self.kiosk("4821").status_code, 200)
        for _ in range(3):
            self.assertEqual(self.kiosk("0000").status_code, 400)
        self.assertNotIn("Too many", json_text(self.kiosk("0000")))                          # 4th fail since the reset, not yet locked

    def test_malformed_pin_and_people_without_a_pin(self):
        for bad in ("", "12", "abcd", "1234567"):
            self.assertEqual(self.kiosk(bad).status_code, 400, bad)
        nobody = self.hire(self.a, "No Pin Guy")
        self.assertEqual(self.kiosk("1357").status_code, 400)
        self.assertFalse(Employee.objects.get(pk=nobody["id"]).pin_hash)

    def test_same_pin_allowed_at_another_branch_but_not_the_same_one(self):
        second = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123456")
        far = self.hire(self.a, "Far Away", loc=second)
        self.assertEqual(self.set_pin(far["id"], "4821").status_code, 200)
        self.assertEqual(self.set_pin(self.hire(self.a, "Close By")["id"], "4821").status_code, 400)

    def test_inactive_people_do_not_block_or_use_a_pin(self):
        self.a.patch(f"/api/v1/staff/employees/{self.emp['id']}/", {"is_active": False}, format="json")
        self.assertEqual(self.kiosk("4821").status_code, 400)
        self.assertEqual(self.set_pin(self.hire(self.a, "Takes Over")["id"], "4821").status_code, 200)

    def test_kiosk_access(self):
        self.assertEqual(self.kiosk("4821", client=self.b).status_code, 404)                 # another restaurant's tablet cannot use this branch
        second = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123456")
        self.assertEqual(self.kiosk("4821", loc=second).status_code, 404)                    # tablet staff only work at their own branch
        self.assertEqual(self.a.post("/api/v1/staff/attendance/kiosk/", {"location": "abc", "pin": "4821"}, format="json").status_code, 400)

    def test_kiosk_follows_the_same_rules_as_a_manager_punch(self):
        self.a.post("/api/v1/staff/attendance/mark/", {"employee": self.emp["id"], "date": THU.isoformat(), "status": "LEAVE", "paid": True}, format="json")
        self.now.return_value = at(THU, "12:00")
        self.assertEqual(self.kiosk("4821").status_code, 400)


class PinStorage(AttBase):
    def pin(self, eid, pin, client=None):
        return (client or self.a).post(f"/api/v1/staff/employees/{eid}/set-pin/", {"pin": pin}, format="json")

    def test_pin_is_never_stored_in_plain_text_and_differs_per_person(self):
        other = self.hire(self.a, "Other Person")
        self.assertEqual(self.pin(self.emp["id"], "4821").status_code, 200)
        stored = Employee.objects.get(pk=self.emp["id"]).pin_hash
        self.assertNotIn("4821", stored)
        self.assertTrue(stored.startswith("hmac$"))
        self.assertNotEqual(att.pin_digest(self.emp["id"], "4821"), att.pin_digest(other["id"], "4821"))     # the id acts as a salt
        self.assertNotEqual(att.pin_digest(self.emp["id"], "4821"), att.pin_digest(self.emp["id"], "4822"))

    def test_changing_and_removing_a_pin(self):
        tablet = self.staff("POS_OPERATOR", "tablet2")
        kiosk = lambda pin: tablet.post("/api/v1/staff/attendance/kiosk/", {"location": self.loc_a.id, "pin": pin}, format="json")
        self.pin(self.emp["id"], "1234")
        self.now.return_value = at(THU, "12:00")
        self.assertEqual(kiosk("1234").status_code, 200)
        self.assertEqual(self.pin(self.emp["id"], "5678").status_code, 200)
        self.assertEqual(kiosk("1234").status_code, 400)                                      # the old PIN is dead
        self.assertEqual(self.pin(self.emp["id"], None).status_code, 200)
        self.assertEqual(Employee.objects.get(pk=self.emp["id"]).pin_hash, "")

    def test_pin_rules(self):
        for bad in ("12", "1234567", "12ab", ""):
            self.assertEqual(self.pin(self.emp["id"], bad).status_code, 400, bad)           # an empty box never removes a PIN (only null does)
        self.assertEqual(self.a.post(f"/api/v1/staff/employees/{self.emp['id']}/set-pin/", {}, format="json").status_code, 400)
        self.assertEqual(self.pin(self.emp["id"], "2468").status_code, 200)
        two = self.hire(self.a, "Second Person")
        self.assertEqual(self.pin(two["id"], "2468").status_code, 400)
        self.assertEqual(self.pin(two["id"], "1357", client=self.staff("POS_OPERATOR", "cash_pin")).status_code, 403)
        self.assertEqual(self.pin(two["id"], "1357", client=self.b).status_code, 404)

    def test_identifying_a_pin_stays_fast_with_a_big_team(self):
        for i in range(60):
            e = self.hire(self.a, f"Crew Member {i}")
            att.set_pin(Employee.objects.get(pk=e["id"]), f"{3000 + i}")
        self.now.return_value = at(THU, "12:00")
        tablet = self.staff("POS_OPERATOR", "tablet3")
        started = _time.monotonic()
        r = tablet.post("/api/v1/staff/attendance/kiosk/", {"location": self.loc_a.id, "pin": "3059"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertLess(_time.monotonic() - started, 1.0)                                     # a slow password hash would take many seconds here


class MarkAndEdit(AttBase):
    def mark(self, status, day=WED, **extra):
        return self.a.post("/api/v1/staff/attendance/mark/", {"employee": self.emp["id"], "date": day.isoformat(), "status": status, **extra}, format="json")

    def test_absent_paid_and_unpaid_leave(self):
        self.assertEqual(self.mark("ABSENT", MON).status_code, 201)
        r = self.mark("LEAVE", TUE, paid=True, note="Wedding")
        self.assertEqual((r.status_code, r.json()["paid_leave"], r.json()["note"]), (201, True, "Wedding"))
        self.assertFalse(self.mark("LEAVE", WED, paid=False).json()["paid_leave"])
        self.assertEqual(AuditLog.objects.filter(action="attendance_marked").count(), 3)

    def test_marking_again_updates_and_present_days_are_protected(self):
        self.mark("ABSENT")
        self.assertEqual(self.mark("LEAVE", paid=True).json()["status"], "LEAVE")
        self.assertEqual(AttendanceRecord.objects.filter(employee_id=self.emp["id"], date=WED).count(), 1)
        self.day(TUE, "12:00", "22:00")
        self.assertEqual(self.mark("ABSENT", TUE).status_code, 400)

    def test_rules(self):
        self.assertEqual(self.mark("ABSENT", FRI).status_code, 400)                           # absent tomorrow makes no sense
        self.assertEqual(self.mark("LEAVE", FRI, paid=True).status_code, 201)                 # planned leave is fine
        self.assertEqual(self.mark("PRESENT").status_code, 400)
        self.assertEqual(self.a.post("/api/v1/staff/attendance/mark/", {"employee": self.emp["id"], "status": "ABSENT"}, format="json").status_code, 400)
        cashier = self.staff("POS_OPERATOR", "cash_mark")
        r = cashier.post("/api/v1/staff/attendance/mark/", {"employee": self.emp["id"], "date": WED.isoformat(), "status": "ABSENT"}, format="json")
        self.assertEqual(r.status_code, 403)
        r = self.b.post("/api/v1/staff/attendance/mark/", {"employee": self.emp["id"], "date": WED.isoformat(), "status": "ABSENT"}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_corrections_need_a_reason_recalculate_and_are_audited(self):
        rec = self.day(WED, "12:00", "22:00")
        url = f"/api/v1/staff/attendance/{rec['id']}/"
        self.assertEqual(self.a.patch(url, {"check_out": iso(WED, "23:00")}, format="json").status_code, 400)       # no reason
        r = self.a.patch(url, {"check_out": iso(WED, "23:00"), "reason": "Stayed to clean"}, format="json")
        self.assertEqual((r.status_code, r.json()["overtime_minutes"], r.json()["worked_minutes"]), (200, 60, 660))
        log = AuditLog.objects.filter(action="attendance_edited").latest("id")
        self.assertEqual(log.details["reason"], "Stayed to clean")
        self.assertIn("22:00", log.details["old"]["check_out"].replace("+05:00", ""))
        self.assertIn("23:00", log.details["new"]["check_out"].replace("+05:00", ""))

    def test_correction_rules(self):
        rec = self.day(WED, "12:00", "22:00")
        url = f"/api/v1/staff/attendance/{rec['id']}/"
        self.assertEqual(self.a.patch(url, {"check_out": iso(WED, "11:00"), "reason": "typo"}, format="json").status_code, 400)
        self.assertEqual(self.a.patch(url, {"check_in": iso(FRI, "12:00"), "check_out": None, "reason": "typo"}, format="json").status_code, 400)   # future
        r = self.a.patch(url, {"status": "ABSENT", "reason": "Entered by mistake"}, format="json")
        self.assertEqual((r.json()["status"], r.json()["check_in"], r.json()["worked_minutes"]), ("ABSENT", None, 0))
        r = self.a.patch(url, {"status": "PRESENT", "reason": "Was actually here"}, format="json")
        self.assertEqual(r.status_code, 400)                                                 # present needs a check-in time
        r = self.a.patch(url, {"status": "PRESENT", "check_in": iso(WED, "12:30"), "check_out": iso(WED, "22:00"), "reason": "Was actually here"}, format="json")
        self.assertEqual((r.status_code, r.json()["late_minutes"]), (200, 30))
        r = self.a.patch(url, {"status": "LEAVE", "paid_leave": True, "reason": "Approved later"}, format="json")
        self.assertEqual((r.json()["status"], r.json()["paid_leave"], r.json()["worked_minutes"]), ("LEAVE", True, 0))

    def test_corrections_are_for_managers_of_the_right_restaurant(self):
        rec = self.day(WED, "12:00", "22:00")
        url = f"/api/v1/staff/attendance/{rec['id']}/"
        self.assertEqual(self.staff("POS_OPERATOR", "cash_edit").patch(url, {"status": "ABSENT", "reason": "nope"}, format="json").status_code, 403)
        self.assertEqual(self.b.patch(url, {"status": "ABSENT", "reason": "nope"}, format="json").status_code, 404)


class Board(AttBase):
    def test_states_through_a_working_day(self):
        eid = self.emp["id"]
        self.now.return_value = at(THU, "09:00")
        self.assertEqual(self.board()[0][eid]["state"], "UPCOMING")
        self.now.return_value = at(THU, "12:30")
        self.assertEqual(self.board()[0][eid]["state"], "NOT_IN")
        self.punch("IN", THU, "12:32")
        rows, _ = self.board()
        self.assertEqual((rows[eid]["state"], rows[eid]["record"]["late_minutes"]), ("ON_DUTY", 32))
        self.punch("OUT", THU, "22:00")
        self.assertEqual(self.board()[0][eid]["state"], "DONE")

    def test_nobody_came(self):
        self.now.return_value = at(THU, "23:00")
        self.assertEqual(self.board()[0][self.emp["id"]]["state"], "ABSENT_DERIVED")
        self.assertEqual(self.board(WED)[0][self.emp["id"]]["state"], "ABSENT_DERIVED")

    def test_off_day_future_unjoined_and_no_schedule(self):
        free = self.hire(self.a, "No Schedule")
        newbie = self.hire(self.a, "Joins Later", joining_date="2026-10-20"); self.put_schedule(newbie["id"])
        self.now.return_value = at(THU, "23:00")
        rows, body = self.board(SUN)
        self.assertEqual((rows[self.emp["id"]]["state"], rows[free["id"]]["state"]), ("OFF", "NO_SCHEDULE"))
        self.assertEqual(self.board(THU)[0][newbie["id"]]["state"], "NOT_JOINED")
        self.assertEqual(self.board(date(2026, 10, 26))[0][self.emp["id"]]["state"], "UPCOMING")      # a future Monday

    def test_counts_leave_and_absent_marks(self):
        other = self.hire(self.a, "Second"); self.put_schedule(other["id"])
        self.now.return_value = at(THU, "13:00")
        self.punch("IN", THU, "12:00")
        self.a.post("/api/v1/staff/attendance/mark/", {"employee": other["id"], "date": THU.isoformat(), "status": "LEAVE", "paid": False}, format="json")
        rows, body = self.board()
        self.assertEqual(body["counts"], {"ON_DUTY": 1, "LEAVE": 1})
        self.assertFalse(rows[other["id"]]["record"]["paid_leave"])

    def test_access_and_validation(self):
        self.assertEqual(self.board(client=self.staff("MANAGER", "mgr_board"))[1]["location"], self.loc_a.id)
        cashier = self.staff("POS_OPERATOR", "cash_board")
        self.assertEqual(cashier.get(f"/api/v1/staff/attendance/?location={self.loc_a.id}").status_code, 403)
        self.assertEqual(self.b.get(f"/api/v1/staff/attendance/?location={self.loc_a.id}").status_code, 404)
        self.assertEqual(self.a.get("/api/v1/staff/attendance/").status_code, 400)
        self.assertEqual(self.a.get(f"/api/v1/staff/attendance/?location={self.loc_a.id}&date=nope").status_code, 400)


class Report(AttBase):
    def report(self, start, end, client=None, **q):
        extra = "".join(f"&{k}={v}" for k, v in q.items())
        r = (client or self.a).get(f"/api/v1/staff/attendance/report/?location={self.loc_a.id}&from={start}&to={end}{extra}")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def week(self):
        self.now.return_value = at(THU, "23:30")
        self.day(MON, "11:55", "22:05"); self.day(TUE, "12:25", "22:50")
        self.a.post("/api/v1/staff/attendance/mark/", {"employee": self.emp["id"], "date": WED.isoformat(), "status": "LEAVE", "paid": True}, format="json")
        self.day(SUN, "14:00", "18:00")                                                     # off-day work; Thursday: nobody marked

    def test_week_totals(self):
        self.week()
        row = self.report(SUN, THU)["rows"][0]
        self.assertEqual((row["scheduled_days"], row["present_days"], row["off_days_worked"]), (4, 3, 1))
        self.assertEqual((row["late_days"], row["late_minutes"]), (1, 25))
        self.assertEqual((row["absent_days"], row["leave_paid"], row["leave_unpaid"]), (1, 1, 0))      # Thursday is absent because nobody marked it
        self.assertEqual((row["worked_minutes"], row["overtime_minutes"]), (610 + 625 + 240, 50 + 240))
        self.assertIsNone(row["records"])

    def test_one_employee_with_day_by_day_records(self):
        self.week()
        row = self.report(SUN, THU, employee=self.emp["id"])["rows"][0]
        self.assertEqual([r["date"] for r in row["records"]], ["2026-10-11", "2026-10-12", "2026-10-13", "2026-10-14"])
        self.assertEqual(row["records"][2]["late_minutes"], 25)

    def test_missing_check_outs(self):
        self.now.return_value = at(THU, "23:30")
        self.punch("IN", WED, "12:00")                                                      # left the building without checking out
        self.assertEqual(self.report(WED, THU)["rows"][0]["missing_checkouts"], 1)

    def test_today_is_not_counted_absent_before_duty_ends(self):
        self.now.return_value = at(THU, "15:00")
        row = self.report(THU, THU)["rows"][0]
        self.assertEqual((row["scheduled_days"], row["absent_days"]), (1, 0))               # in progress: "not in yet", not absent

    def test_range_and_scope_rules(self):
        self.assertEqual(self.a.get(f"/api/v1/staff/attendance/report/?location={self.loc_a.id}&from=2026-10-15&to=2026-10-01").status_code, 400)
        self.assertEqual(self.a.get(f"/api/v1/staff/attendance/report/?location={self.loc_a.id}&from=2020-01-01&to=2026-10-15").status_code, 400)
        self.assertEqual(self.a.get(f"/api/v1/staff/attendance/report/?location={self.loc_a.id}&from=x&to=2026-10-15").status_code, 400)
        cashier = self.staff("POS_OPERATOR", "cash_rep")
        self.assertEqual(cashier.get(f"/api/v1/staff/attendance/report/?location={self.loc_a.id}").status_code, 403)
        self.assertEqual(self.b.get(f"/api/v1/staff/attendance/report/?location={self.loc_a.id}").status_code, 404)
        second = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123456")
        far = self.hire(self.a, "Far Away", loc=second)
        self.assertEqual(self.a.get(f"/api/v1/staff/attendance/report/?location={self.loc_a.id}&employee={far['id']}").status_code, 400)

    def test_inactive_people_with_records_stay_in_the_report(self):
        self.now.return_value = at(THU, "23:30")
        self.day(MON, "12:00", "22:00")
        self.a.patch(f"/api/v1/staff/employees/{self.emp['id']}/", {"is_active": False}, format="json")
        self.assertEqual([r["employee"]["name"] for r in self.report(MON, THU)["rows"]], ["Ali Waiter"])
        self.assertEqual(self.report(WED, THU)["rows"], [])


class ScheduleApi(AttBase):
    def test_put_get_delete(self):
        e = self.hire(self.a, "Chef Chaudhry", "CHEF")
        self.assertIsNone(self.a.get(f"/api/v1/staff/employees/{e['id']}/schedule/").json()["schedule"])
        s = self.put_schedule(e["id"], weekly_off=[4, 0, 0], overtime_multiplier=2)["schedule"]
        self.assertEqual((s["weekly_off"], s["overtime_multiplier"], s["overnight"]), ([0, 4], 2.0, False))
        self.assertEqual(self.a.delete(f"/api/v1/staff/employees/{e['id']}/schedule/").status_code, 204)
        self.assertIsNone(self.a.get(f"/api/v1/staff/employees/{e['id']}/schedule/").json()["schedule"])

    def test_validation(self):
        put = lambda **kw: self.a.put(f"/api/v1/staff/employees/{self.emp['id']}/schedule/", {**SCHED, **kw}, format="json").status_code
        self.assertEqual(put(end_time="12:00"), 400)
        self.assertEqual(put(start_time="noon"), 400)
        self.assertEqual(put(weekly_off=[7]), 400)
        self.assertEqual(put(weekly_off="Sunday"), 400)
        self.assertEqual(put(grace_minutes=500), 400)
        self.assertEqual(put(overtime_multiplier=0.5), 400)
        self.assertEqual(put(min_overtime_minutes="x"), 400)
        self.assertEqual(put(), 200)

    def test_bulk(self):
        w2 = self.hire(self.a, "Waiter Two"); chef = self.hire(self.a, "A Chef", "CHEF")
        r = self.a.post("/api/v1/staff/schedule/bulk/", {**SCHED, "location": self.loc_a.id, "role": "WAITER", "start_time": "17:00", "end_time": "23:30"}, format="json")
        self.assertEqual((r.status_code, r.json()["updated"]), (200, 2))
        sched = lambda eid: self.a.get(f"/api/v1/staff/employees/{eid}/schedule/").json()["schedule"]
        self.assertEqual(sched(w2["id"])["start_time"], "17:00")
        self.assertIsNone(sched(chef["id"]))
        self.assertEqual(self.a.post("/api/v1/staff/schedule/bulk/", {**SCHED, "location": self.loc_a.id}, format="json").json()["updated"], 3)
        self.assertEqual(self.a.post("/api/v1/staff/schedule/bulk/", {**SCHED, "location": self.loc_a.id, "role": "WIZARD"}, format="json").status_code, 400)

    def test_permissions(self):
        cashier = self.staff("POS_OPERATOR", "cash_sched")
        url = f"/api/v1/staff/employees/{self.emp['id']}/schedule/"
        self.assertEqual(cashier.put(url, SCHED, format="json").status_code, 403)
        self.assertEqual(cashier.delete(url).status_code, 403)
        self.assertEqual(cashier.post("/api/v1/staff/schedule/bulk/", {**SCHED, "location": self.loc_a.id}, format="json").status_code, 403)
        self.assertEqual(self.b.put(url, SCHED, format="json").status_code, 404)
        self.assertEqual(self.b.post("/api/v1/staff/schedule/bulk/", {**SCHED, "location": self.loc_a.id}, format="json").status_code, 404)

    def test_employee_detail_shows_schedule_and_todays_state(self):
        self.now.return_value = at(THU, "13:00")
        self.punch("IN", THU, "12:03")
        d = self.a.get(f"/api/v1/staff/employees/{self.emp['id']}/").json()
        self.assertEqual((d["schedule"]["start_time"], d["today"]["state"], d["today"]["record"]["late_minutes"]), ("12:00", "ON_DUTY", 0))
