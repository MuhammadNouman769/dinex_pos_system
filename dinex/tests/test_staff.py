"""Phase 5.1: employees, waiter on orders, riders, delivery flow and rider cash settlement."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.cash.models import AuditLog, Payment
from apps.orders.models import Order
from apps.organizations.models import Location
from apps.staff.models import Employee, RiderSettlement
from tests.base import TenantTestCase, PASSWORD

User = get_user_model()
ADDR = {"customer_phone": "03001112222", "delivery_address": "House 1, Street 2, Gulberg, Lahore"}


class StaffBase(TenantTestCase):
    def hire(self, client, name, role="WAITER", loc=None, **extra):
        r = client.post("/api/v1/staff/employees/", {"name": name, "role": role, "location": (loc or self.loc_a).id, **extra}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def login_staff(self, role, username, loc=None):
        r = self.a.post("/api/v1/organizations/location-staff/", {
            "username": username, "email": f"{username}@x.com", "password": PASSWORD, "first_name": "S", "last_name": "T",
            "location_id": (loc or self.loc_a).id, "role": role}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return self.as_user(User.objects.get(username=username))

    def delivery(self, client=None, qty=1, rider=None, pay=None, upto=None):
        """A delivery order; optionally with a rider, prepaid, and moved up to a status."""
        client = client or self.a
        o = client.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "DELIVERY", **ADDR}, format="json")
        self.assertEqual(o.status_code, 201, o.content)
        o = o.json()
        self.assertEqual(self.add_item(client, o["id"], self.variant_a, qty).status_code, 201)
        if rider:
            r = client.post(f"/api/v1/staff/orders/{o['id']}/assign-rider/", {"rider": rider}, format="json")
            self.assertEqual(r.status_code, 200, r.content)
        if pay:
            self.assertEqual(self.pay(client, o["id"], pay).status_code, 201)
        for st in ("CONFIRMED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "COMPLETED"):
            if upto is None:
                break
            self.assertEqual(client.post(f"/api/v1/orders/{o['id']}/status/", {"status": st}, format="json").status_code, 200, st)
            if st == upto:
                break
        return o


class EmployeeCrud(StaffBase):
    def test_codes_are_sequential_and_never_reused(self):
        a, b = self.hire(self.a, "Ali Waiter"), self.hire(self.a, "Bilal Chef", "CHEF")
        self.assertEqual((a["code"], b["code"]), ("E-001", "E-002"))
        self.assertEqual(self.a.delete(f"/api/v1/staff/employees/{b['id']}/").status_code, 204)
        self.assertEqual(self.hire(self.a, "Cara Cook", "CHEF")["code"], "E-003")
        self.assertEqual(self.hire(self.b, "Other Org Waiter", loc=self.loc_b)["code"], "E-001")     # each restaurant counts on its own

    def test_validation(self):
        bad = lambda **kw: self.a.post("/api/v1/staff/employees/", {"name": "Test Person", "role": "WAITER", "location": self.loc_a.id, **kw}, format="json").status_code
        self.assertEqual(bad(name=" "), 400)
        self.assertEqual(bad(phone="abc"), 400)
        self.assertEqual(bad(cnic="123"), 400)
        self.assertEqual(bad(role="ASTRONAUT"), 400)
        self.assertEqual(bad(delivery_commission="30"), 400)                 # waiters get no delivery commission
        e = self.hire(self.a, "Rida Rider", "RIDER", delivery_commission="40", cnic="4210112345671", phone="0300-1234567")
        self.assertEqual((e["cnic"], Decimal(e["delivery_commission"])), ("42101-1234567-1", Decimal("40")))

    def test_list_filters_and_search(self):
        self.hire(self.a, "Ali Raza", "WAITER"); self.hire(self.a, "Sana Gul", "RIDER"); self.hire(self.a, "Zed Chef", "CHEF", phone="03211234567")
        names = lambda q: sorted(e["name"] for e in self.a.get(f"/api/v1/staff/employees/{q}").json()["results"])
        self.assertEqual(names("?role=RIDER"), ["Sana Gul"])
        self.assertEqual(names("?search=zed"), ["Zed Chef"])
        self.assertEqual(names("?search=0321"), ["Zed Chef"])
        self.assertEqual(len(names("")), 3)
        self.assertEqual(self.a.get("/api/v1/staff/employees/?role=NOPE").status_code, 400)
        self.assertEqual(self.a.get("/api/v1/staff/employees/?location=abc").status_code, 400)

    def test_edit_deactivate_and_hidden_from_default_list(self):
        e = self.hire(self.a, "Old Hand")
        r = self.a.patch(f"/api/v1/staff/employees/{e['id']}/", {"phone": "03001234567", "is_active": False}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.a.get("/api/v1/staff/employees/").json()["count"], 0)
        self.assertEqual(self.a.get("/api/v1/staff/employees/?active=false").json()["count"], 1)

    def test_permissions(self):
        e = self.hire(self.a, "Target")
        cashier = self.login_staff("POS_OPERATOR", "cash_s1")
        self.assertEqual(cashier.get("/api/v1/staff/employees/").status_code, 200)            # POS needs the waiter list
        self.assertEqual(cashier.post("/api/v1/staff/employees/", {"name": "New Guy", "role": "WAITER", "location": self.loc_a.id}, format="json").status_code, 403)
        self.assertEqual(cashier.patch(f"/api/v1/staff/employees/{e['id']}/", {"name": "X Y"}, format="json").status_code, 403)
        self.assertEqual(cashier.delete(f"/api/v1/staff/employees/{e['id']}/").status_code, 403)
        manager = self.login_staff("MANAGER", "mgr_s1")
        self.assertEqual(manager.post("/api/v1/staff/employees/", {"name": "By Manager", "role": "WAITER", "location": self.loc_a.id}, format="json").status_code, 201)

    def test_manager_only_manages_own_branch_and_tenants_are_isolated(self):
        other = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123456")
        manager = self.login_staff("MANAGER", "mgr_s2")
        r = manager.post("/api/v1/staff/employees/", {"name": "Wrong Branch", "role": "WAITER", "location": other.id}, format="json")
        self.assertEqual(r.status_code, 400)                                                  # not even a valid choice for them
        e = self.hire(self.a, "Mine")
        self.assertEqual(self.b.get(f"/api/v1/staff/employees/{e['id']}/").status_code, 404)
        self.assertEqual(self.b.patch(f"/api/v1/staff/employees/{e['id']}/", {"name": "Hack Hack"}, format="json").status_code, 404)
        self.assertEqual(self.b.get("/api/v1/staff/employees/").json()["count"], 0)
        r = self.b.post("/api/v1/staff/employees/", {"name": "Intruder", "role": "WAITER", "location": self.loc_a.id}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_link_login(self):
        e = self.hire(self.a, "Has Login", "MANAGER")
        mgr = self.login_staff("MANAGER", "linked_mgr")
        uid = User.objects.get(username="linked_mgr").id
        url = f"/api/v1/staff/employees/{e['id']}/link-user/"
        self.assertEqual(mgr.post(url, {"user_id": uid}, format="json").status_code, 403)          # owner only
        self.assertEqual(self.a.post(url, {"user_id": self.owner_b.id}, format="json").status_code, 400)   # other restaurant's user
        r = self.a.post(url, {"user_id": uid}, format="json")
        self.assertEqual((r.status_code, r.json()["username"]), (200, "linked_mgr"))
        e2 = self.hire(self.a, "Second")
        self.assertEqual(self.a.post(f"/api/v1/staff/employees/{e2['id']}/link-user/", {"user_id": uid}, format="json").status_code, 400)   # already used
        self.assertIsNone(self.a.post(url, {"user_id": None}, format="json").json()["username"])


class WaiterOnOrders(StaffBase):
    def setUp(self):
        self.w = self.hire(self.a, "Waiter Wali")

    def test_order_remembers_which_waiter_took_it(self):
        o = self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "TAKEAWAY", "waiter": self.w["id"]}, format="json")
        self.assertEqual(o.status_code, 201, o.content)
        self.assertEqual((o.json()["waiter"], o.json()["waiter_name"]), (self.w["id"], "Waiter Wali"))
        listed = self.a.get("/api/v1/orders/").json()["results"][0]
        self.assertEqual(listed["waiter_name"], "Waiter Wali")

    def test_waiter_must_be_valid(self):
        second = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123456")
        other_branch = self.hire(self.a, "Other Branch Waiter", loc=second)
        rider = self.hire(self.a, "A Rider", "RIDER")
        foreign = self.hire(self.b, "Foreign Waiter", loc=self.loc_b)
        inactive = self.hire(self.a, "Gone Waiter"); self.a.patch(f"/api/v1/staff/employees/{inactive['id']}/", {"is_active": False}, format="json")
        for bad in (other_branch, rider, foreign, inactive):
            r = self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "TAKEAWAY", "waiter": bad["id"]}, format="json")
            self.assertEqual(r.status_code, 400, (bad["name"], r.content))

    def test_change_waiter_and_stats(self):
        w2 = self.hire(self.a, "Second Waiter")
        o = self.new_order(self.a, self.loc_a, waiter=self.w["id"])
        self.add_item(self.a, o["id"], self.variant_a, 2)                                    # 1100
        c = self.new_order(self.a, self.loc_a, waiter=self.w["id"])
        self.add_item(self.a, c["id"], self.variant_a, 1)
        self.a.post(f"/api/v1/orders/{c['id']}/status/", {"status": "CANCELLED", "reason": "customer left"}, format="json")
        st = self.a.get(f"/api/v1/staff/employees/{self.w['id']}/").json()["stats"]
        self.assertEqual((st["kind"], st["orders_30d"], Decimal(st["sales_30d"])), ("waiter", 1, Decimal("1100.00")))   # cancelled excluded
        self.assertEqual(self.a.patch(f"/api/v1/orders/{o['id']}/", {"waiter": w2["id"]}, format="json").status_code, 200)
        self.assertEqual(self.a.get(f"/api/v1/staff/employees/{self.w['id']}/").json()["stats"]["orders_30d"], 0)
        self.assertEqual(self.a.get(f"/api/v1/staff/employees/{w2['id']}/").json()["stats"]["orders_30d"], 1)

    def test_cannot_deactivate_while_on_an_open_order_but_old_orders_keep_the_name(self):
        o = self.new_order(self.a, self.loc_a, waiter=self.w["id"])
        r = self.a.patch(f"/api/v1/staff/employees/{self.w['id']}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("open order", r.json()["detail"])
        self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": "CANCELLED", "reason": "test cancel"}, format="json")
        self.assertEqual(self.a.delete(f"/api/v1/staff/employees/{self.w['id']}/").status_code, 204)
        self.assertEqual(self.a.get(f"/api/v1/orders/{o['id']}/").json()["waiter_name"], "Waiter Wali")


class RiderAssignment(StaffBase):
    def setUp(self):
        self.r1 = self.hire(self.a, "Rider Ali", "RIDER")
        self.r2 = self.hire(self.a, "Rider Bilal", "RIDER")
        self.assign = lambda client, oid, rider: client.post(f"/api/v1/staff/orders/{oid}/assign-rider/", {"rider": rider}, format="json")

    def test_assign_and_dispatch_flow_records_times(self):
        o = self.delivery(rider=self.r1["id"], upto="READY")
        r = self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": "OUT_FOR_DELIVERY"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        order = Order.objects.get(pk=o["id"])
        self.assertIsNotNone(order.dispatched_at)
        self.assertIsNone(order.delivered_at)
        self.assertEqual(self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": "COMPLETED"}, format="json").status_code, 200)
        order.refresh_from_db()
        self.assertIsNotNone(order.delivered_at)
        d = self.a.get(f"/api/v1/orders/{o['id']}/").json()
        self.assertEqual((d["rider_name"], d["rider"]), ("Rider Ali", self.r1["id"]))

    def test_cannot_go_out_without_a_rider(self):
        o = self.delivery(upto="READY")
        r = self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": "OUT_FOR_DELIVERY"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("rider", r.json()["error"].lower())

    def test_rider_choice_rules(self):
        take = self.new_order(self.a, self.loc_a)
        self.assertEqual(self.assign(self.a, take["id"], self.r1["id"]).status_code, 400)               # not a delivery order
        o = self.delivery()
        waiter = self.hire(self.a, "Not A Rider")
        foreign = self.hire(self.b, "Foreign Rider", "RIDER", loc=self.loc_b)
        second = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123456")
        far = self.hire(self.a, "Far Rider", "RIDER", loc=second)
        for bad in (waiter, foreign, far):
            self.assertEqual(self.assign(self.a, o["id"], bad["id"]).status_code, 400, bad["name"])
        self.assertEqual(self.assign(self.a, o["id"], self.r1["id"]).status_code, 200)
        self.assertEqual(self.assign(self.a, o["id"], self.r2["id"]).json()["rider_name"], "Rider Bilal")   # reassign before dispatch
        self.assertIsNone(self.assign(self.a, o["id"], None).json()["rider"])
        self.assertEqual(self.b.post(f"/api/v1/staff/orders/{o['id']}/assign-rider/", {"rider": foreign["id"]}, format="json").status_code, 404)

    def test_after_dispatch_only_a_manager_can_change_the_rider(self):
        cashier = self.login_staff("POS_OPERATOR", "cash_r1")
        o = self.delivery(rider=self.r1["id"], upto="OUT_FOR_DELIVERY")
        self.assertEqual(self.assign(cashier, o["id"], self.r2["id"]).status_code, 403)
        self.assertEqual(self.assign(self.a, o["id"], None).status_code, 400)                       # cannot unassign a rider who left
        self.assertEqual(self.assign(self.a, o["id"], self.r2["id"]).status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="rider_reassigned").exists())

    def test_finished_orders_cannot_be_reassigned_and_takeaway_still_needs_payment(self):
        o = self.delivery(rider=self.r1["id"], upto="COMPLETED")
        self.assertEqual(self.assign(self.a, o["id"], self.r2["id"]).status_code, 400)
        self.open_shift(self.a, self.loc_a)
        t = self.new_order(self.a, self.loc_a)
        self.add_item(self.a, t["id"], self.variant_a, 1)
        for st in ("CONFIRMED", "PREPARING", "READY"):
            self.a.post(f"/api/v1/orders/{t['id']}/status/", {"status": st}, format="json")
        self.assertEqual(self.a.post(f"/api/v1/orders/{t['id']}/status/", {"status": "COMPLETED"}, format="json").status_code, 400)

    def test_rider_cannot_be_removed_while_on_the_road(self):
        self.delivery(rider=self.r1["id"], upto="OUT_FOR_DELIVERY")
        self.assertEqual(self.a.delete(f"/api/v1/staff/employees/{self.r1['id']}/").status_code, 400)


class RiderCash(StaffBase):
    def setUp(self):
        self.r1 = self.hire(self.a, "Rider Ali", "RIDER")
        self.r2 = self.hire(self.a, "Rider Bilal", "RIDER")
        self.settle = lambda client, rid, **b: client.post(f"/api/v1/staff/riders/{rid}/settle/", b, format="json")

    def test_cash_on_delivery_is_owed_by_the_rider_until_settled(self):
        o1 = self.delivery(rider=self.r1["id"], qty=1, upto="COMPLETED")            # 550
        o2 = self.delivery(rider=self.r1["id"], qty=2, upto="COMPLETED")            # 1100
        self.delivery(rider=self.r1["id"], qty=1, upto="OUT_FOR_DELIVERY")          # still on the road
        self.open_shift(self.a, self.loc_a)
        prepaid = self.delivery(rider=self.r1["id"], qty=1, pay="CARD", upto="COMPLETED")        # paid online: rider owes nothing
        self.delivery(rider=self.r2["id"], qty=3, upto="COMPLETED")                              # a different rider's cash
        led = self.a.get(f"/api/v1/staff/riders/{self.r1['id']}/ledger/").json()
        self.assertEqual([o["id"] for o in led["orders"]], [o1["id"], o2["id"]])
        self.assertEqual(Decimal(led["summary"]["to_settle"]), Decimal("1650.00"))
        self.assertEqual((led["summary"]["on_road"], led["summary"]["delivered_today"]), (1, 3))
        riders = {r["name"]: r["summary"] for r in self.a.get("/api/v1/staff/riders/").json()}
        self.assertEqual(Decimal(riders["Rider Bilal"]["to_settle"]), Decimal("1650.00"))

    def test_full_settlement_records_cash_in_the_cashiers_shift(self):
        o1 = self.delivery(rider=self.r1["id"], qty=1, upto="COMPLETED"); o2 = self.delivery(rider=self.r1["id"], qty=2, upto="COMPLETED")
        shift = self.open_shift(self.a, self.loc_a, "1000")
        r = self.settle(self.a, self.r1["id"], handed="1650", note="evening")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual((Decimal(r.json()["expected"]), Decimal(r.json()["handed"]), Decimal(r.json()["shortage"])), (Decimal("1650"), Decimal("1650"), Decimal("0")))
        for o in (o1, o2):
            self.assertEqual(Order.objects.get(pk=o["id"]).payment_status, "PAID")
        self.assertEqual(Decimal(r.json()["summary"]["to_settle"]), Decimal("0"))
        pays = Payment.objects.filter(order_id__in=[o1["id"], o2["id"]])
        self.assertEqual({(p.method, p.kind, p.shift_id) for p in pays}, {("CASH", "PAYMENT", shift["id"])})
        self.assertTrue(all(p.reference.startswith("RS-") for p in pays))
        live = self.a.get(f"/api/v1/cash/shifts/{shift['id']}/").json()
        self.assertEqual(Decimal(live["expected_cash"]), Decimal("2650.00"))                    # 1000 + 1650: the drawer includes it
        self.assertEqual(self.settle(self.a, self.r1["id"], handed="1").status_code, 400)       # nothing left to settle

    def test_short_settlement_keeps_the_shortage_on_the_oldest_orders(self):
        o1 = self.delivery(rider=self.r1["id"], qty=1, upto="COMPLETED"); o2 = self.delivery(rider=self.r1["id"], qty=2, upto="COMPLETED")   # 550, 1100
        self.open_shift(self.a, self.loc_a)
        r = self.settle(self.a, self.r1["id"], handed="1500")                                   # Rs 150 short
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Decimal(r.json()["shortage"]), Decimal("150"))
        self.assertEqual(Order.objects.get(pk=o1["id"]).payment_status, "PAID")                 # oldest paid first
        o2.update(Order.objects.filter(pk=o2["id"]).values("payment_status").get())
        self.assertEqual(o2["payment_status"], "PARTIAL")
        led = self.a.get(f"/api/v1/staff/riders/{self.r1['id']}/ledger/").json()
        self.assertEqual((len(led["orders"]), Decimal(led["orders"][0]["due"])), (1, Decimal("150.00")))
        self.assertEqual(Decimal(led["settlements"][0]["shortage"]), Decimal("150"))
        self.assertTrue(AuditLog.objects.filter(action="rider_shortage").exists())
        # the rider later brings the rest
        self.assertEqual(Decimal(str(self.settle(self.a, self.r1["id"], handed="150").json()["shortage"])), Decimal("0"))

    def test_settle_only_selected_orders(self):
        o1 = self.delivery(rider=self.r1["id"], qty=1, upto="COMPLETED"); o2 = self.delivery(rider=self.r1["id"], qty=1, upto="COMPLETED")
        self.open_shift(self.a, self.loc_a)
        self.assertEqual(self.settle(self.a, self.r1["id"], handed="550", order_ids=[o2["id"]]).status_code, 201)
        self.assertEqual(Order.objects.get(pk=o2["id"]).payment_status, "PAID")
        self.assertEqual(Order.objects.get(pk=o1["id"]).payment_status, "PENDING")

    def test_settlement_rules(self):
        o = self.delivery(rider=self.r1["id"], qty=1, upto="COMPLETED")
        self.assertEqual(self.settle(self.a, self.r1["id"], handed="550").status_code, 400)                       # no open shift
        self.open_shift(self.a, self.loc_a)
        self.assertEqual(self.settle(self.a, self.r1["id"], handed="9999").status_code, 400)                      # more than owed
        self.assertEqual(self.settle(self.a, self.r1["id"], handed="-5").status_code, 400)
        self.assertEqual(self.settle(self.a, self.r1["id"]).status_code, 400)                                      # amount missing
        self.assertEqual(self.settle(self.a, self.r1["id"], handed="550", order_ids=[999999]).status_code, 400)   # not this rider's
        self.assertEqual(self.settle(self.a, self.r1["id"], handed="550", order_ids=[]).status_code, 400)
        waiter = self.hire(self.a, "Not Rider")
        self.assertEqual(self.settle(self.a, waiter["id"], handed="1").status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)                                                              # nothing half-done
        self.assertEqual(RiderSettlement.objects.count(), 0)

    def test_other_restaurant_cannot_settle_my_rider(self):
        self.delivery(rider=self.r1["id"], qty=1, upto="COMPLETED")
        self.open_shift(self.b, self.loc_b)
        self.assertEqual(self.settle(self.b, self.r1["id"], handed="550").status_code, 404)
        self.assertEqual(self.b.get(f"/api/v1/staff/riders/{self.r1['id']}/ledger/").status_code, 404)

    def test_rider_who_owes_cash_cannot_be_removed_or_change_role(self):
        self.delivery(rider=self.r1["id"], qty=1, upto="COMPLETED")
        self.assertEqual(self.a.delete(f"/api/v1/staff/employees/{self.r1['id']}/").status_code, 400)
        self.assertEqual(self.a.patch(f"/api/v1/staff/employees/{self.r1['id']}/", {"is_active": False}, format="json").status_code, 400)
        self.assertEqual(self.a.patch(f"/api/v1/staff/employees/{self.r1['id']}/", {"role": "WAITER"}, format="json").status_code, 400)
        self.open_shift(self.a, self.loc_a)
        self.settle(self.a, self.r1["id"], handed="550")
        self.assertEqual(self.a.delete(f"/api/v1/staff/employees/{self.r1['id']}/").status_code, 204)

    def test_delivery_time_stats(self):
        o = self.delivery(rider=self.r1["id"], upto="COMPLETED")
        now = timezone.now()
        Order.objects.filter(pk=o["id"]).update(dispatched_at=now - timezone.timedelta(minutes=30), delivered_at=now)
        s = self.a.get(f"/api/v1/staff/employees/{self.r1['id']}/").json()["stats"]
        self.assertEqual((s["kind"], s["delivered_30d"], s["avg_delivery_minutes"]), ("rider", 1, 30.0))

    def test_cashier_of_another_branch_cannot_settle(self):
        second = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123456")
        self.delivery(rider=self.r1["id"], qty=1, upto="COMPLETED")
        other_cashier = self.login_staff("POS_OPERATOR", "cash_far", loc=second)
        self.open_shift(other_cashier, second)
        self.assertEqual(self.settle(other_cashier, self.r1["id"], handed="550").status_code, 404)
