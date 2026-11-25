"""Dish options on orders, table transfer and bill splitting."""
import uuid
from decimal import Decimal

from apps.catalog.models import ModifierGroup, ModifierOption, ProductModifierGroup
from apps.orders.models import Order, Table
from tests.base import TenantTestCase

SYNC = "/api/v1/orders/sync/"


class _NoTax:
    def setUp(self):
        super().setUp()
        from apps.organizations.models import Location
        Location.objects.update(tax_rate=0, service_charge_rate=0)

    def variant2(self, name, price, org=None):
        from apps.catalog.models import Product, ProductCategory, ProductVariant
        org = org or self.org_a
        cat, _ = ProductCategory.objects.get_or_create(organization=org, slug="main", defaults={"name": "Main"})
        p = Product.objects.create(organization=org, category=cat, name=name, slug=name.lower(), sku=name.upper())
        return ProductVariant.objects.create(product=p, name="Regular", base_price=price)


class DishOptions(_NoTax, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.product = self.variant_a.product
        self.cheese = self.group("Extras", mn=0, mx=2, opts=[("Extra cheese", 60), ("Extra patty", 150)])
        self.spice = self.group("Spice", mn=1, mx=1, required=True, opts=[("Mild", 0), ("Hot", 0)])

    def group(self, name, mn, mx, opts, required=False, org=None):
        g = ModifierGroup.objects.create(organization=org or self.org_a, name=name, min_selections=mn, max_selections=mx, is_required=required)
        options = [ModifierOption.objects.create(modifier_group=g, name=n, price_adjustment=p, position=i) for i, (n, p) in enumerate(opts)]
        ProductModifierGroup.objects.create(product=self.product, modifier_group=g, display_order=0)
        g.opts = options
        return g

    def order(self, mods, qty=1, **extra):
        body = {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id, "order_type": "TAKEAWAY",
                "items": [{"product_variant": self.variant_a.id, "quantity": qty, "modifiers": mods, **extra}]}
        return self.a.post(SYNC, body, format="json")

    def test_menu_lists_the_option_groups_of_a_dish(self):
        p = next(x for x in self.a.get("/api/v1/catalog/products/").json()["results"] if x["id"] == self.product.id)
        names = {g["name"]: g for g in p["modifier_groups"]}
        self.assertEqual(set(names), {"Extras", "Spice"})
        self.assertTrue(names["Spice"]["required"])
        self.assertEqual([o["name"] for o in names["Extras"]["options"]], ["Extra cheese", "Extra patty"])

    def test_options_are_priced_into_the_line_and_snapshotted(self):
        r = self.order([self.cheese.opts[0].id, self.spice.opts[1].id], qty=2)
        self.assertEqual(r.status_code, 201, r.content)
        it = r.json()["order"]["items"][0]
        self.assertEqual((it["unit_price"], it["total_price"]), ("560.00", "1120.00"))      # 500 + 60, x2
        self.assertEqual([m["name"] for m in it["modifiers"]], ["Extra cheese", "Hot"])
        self.assertEqual(r.json()["order"]["subtotal"], "1120.00")

    def test_changing_the_option_price_later_does_not_change_old_orders(self):
        r = self.order([self.cheese.opts[0].id, self.spice.opts[0].id])
        ModifierOption.objects.filter(pk=self.cheese.opts[0].pk).update(price_adjustment=999)
        it = self.a.get(f"/api/v1/orders/{r.json()['order']['id']}/").json()["items"][0]
        self.assertEqual(it["unit_price"], "560.00")

    def test_required_group_must_be_chosen(self):
        r = self.order([self.cheese.opts[0].id])
        self.assertEqual(r.status_code, 400)
        self.assertIn("Spice", str(r.json()))
        self.assertEqual(Order.objects.count(), 0)

    def test_too_many_choices_and_duplicates_are_refused(self):
        three = self.group("Sauces", 0, 1, [("Mayo", 0), ("Ketchup", 0)])
        self.assertEqual(self.order([self.spice.opts[0].id, three.opts[0].id, three.opts[1].id]).status_code, 400)
        self.assertEqual(self.order([self.spice.opts[0].id, self.spice.opts[0].id]).status_code, 400)

    def test_option_from_another_restaurant_is_refused(self):
        other = ModifierGroup.objects.create(organization=self.org_b, name="X", max_selections=1)
        o = ModifierOption.objects.create(modifier_group=other, name="Steal", price_adjustment=-400)
        r = self.order([self.spice.opts[0].id, o.id])
        self.assertEqual(r.status_code, 400)

    def test_dish_without_options_still_orders_normally(self):
        v = self.variant2("Fries", 200)
        body = {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id, "order_type": "TAKEAWAY", "items": [{"product_variant": v.id, "quantity": 1}]}
        self.assertEqual(self.a.post(SYNC, body, format="json").status_code, 201)

    def test_item_note_is_kept(self):
        r = self.order([self.spice.opts[0].id], notes="no onions")
        self.assertEqual(r.json()["order"]["items"][0]["notes"], "no onions")


class TableTransfer(_NoTax, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.t1 = Table.objects.create(location=self.loc_a, table_number="T-1", capacity=4)
        self.t2 = Table.objects.create(location=self.loc_a, table_number="T-2", capacity=4)
        self.o = self.place(self.t1)

    def place(self, table, qty=1):
        body = {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id, "order_type": "DINE_IN", "table": table.id,
                "items": [{"product_variant": self.variant_a.id, "quantity": qty}]}
        r = self.a.post(SYNC, body, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["order"]

    def url(self, oid):
        return f"/api/v1/orders/{oid}/transfer-table/"

    def test_moves_the_order_and_swaps_table_status(self):
        r = self.a.post(self.url(self.o["id"]), {"table": self.t2.id}, format="json")
        self.assertEqual((r.status_code, r.json()["table"]), (200, self.t2.id))
        self.t1.refresh_from_db(); self.t2.refresh_from_db()
        self.assertEqual((self.t1.status, self.t2.status), ("AVAILABLE", "OCCUPIED"))

    def test_busy_table_is_refused(self):
        self.place(self.t2)
        r = self.a.post(self.url(self.o["id"]), {"table": self.t2.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.t1.refresh_from_db(); self.assertEqual(self.t1.status, "OCCUPIED")

    def test_old_table_stays_busy_while_another_order_uses_it(self):
        self.place(self.t1)                                            # second bill on T-1
        self.a.post(self.url(self.o["id"]), {"table": self.t2.id}, format="json")
        self.t1.refresh_from_db(); self.assertEqual(self.t1.status, "OCCUPIED")

    def test_takeaway_and_closed_orders_cannot_move(self):
        take = self.a.post(SYNC, {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id, "order_type": "TAKEAWAY",
                                  "items": [{"product_variant": self.variant_a.id, "quantity": 1}]}, format="json").json()["order"]
        self.assertEqual(self.a.post(self.url(take["id"]), {"table": self.t2.id}, format="json").status_code, 400)
        Order.objects.filter(pk=self.o["id"]).update(status="CANCELLED")
        self.assertEqual(self.a.post(self.url(self.o["id"]), {"table": self.t2.id}, format="json").status_code, 400)

    def test_other_restaurants_order_is_not_reachable(self):
        self.assertEqual(self.b.post(self.url(self.o["id"]), {"table": self.t2.id}, format="json").status_code, 404)


class SplitBill(_NoTax, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.fries = self.variant2("Fries", 200)
        self.t1 = Table.objects.create(location=self.loc_a, table_number="T-1", capacity=4)
        body = {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id, "order_type": "DINE_IN", "table": self.t1.id, "customer_name": "Group",
                "items": [{"product_variant": self.variant_a.id, "quantity": 3, "notes": "spicy"}, {"product_variant": self.fries.id, "quantity": 2}]}
        self.o = self.a.post(SYNC, body, format="json").json()["order"]          # 3x500 + 2x200 = 1900
        self.items = {i["product_name"]: i["id"] for i in self.o["items"]}

    def split(self, picks, oid=None):
        return self.a.post(f"/api/v1/orders/{oid or self.o['id']}/split/", {"items": picks}, format="json")

    def test_moves_part_of_a_line_to_a_new_bill(self):
        r = self.split([{"item": self.items["Burger"], "quantity": 1}, {"item": self.items["Fries"], "quantity": 2}])
        self.assertEqual(r.status_code, 201, r.content)
        old, new = r.json()["order"], r.json()["new_order"]
        self.assertEqual((old["total_amount"], new["total_amount"]), ("1000.00", "900.00"))
        self.assertEqual(Decimal(old["total_amount"]) + Decimal(new["total_amount"]), Decimal("1900.00"))
        self.assertEqual((new["table"], new["customer_name"], new["status"]), (self.t1.id, "Group", "CONFIRMED"))
        self.assertEqual({(i["product_name"], i["quantity"]) for i in new["items"]}, {("Burger", 1), ("Fries", 2)})
        self.assertEqual([i["notes"] for i in new["items"] if i["product_name"] == "Burger"], ["spicy"])

    def test_each_bill_is_paid_on_its_own_and_table_frees_after_both(self):
        r = self.split([{"item": self.items["Fries"], "quantity": 2}])
        old, new = r.json()["order"], r.json()["new_order"]
        self.open_shift(self.a, self.loc_a)
        for o in (old, new):
            self.assertEqual(self.pay(self.a, o["id"], amount=o["total_amount"]).status_code, 201)
            self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": "PREPARING"}, format="json")
        for o in (old, new):
            for st in ("PREPARING", "READY", "COMPLETED"):
                self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": st}, format="json")
            if o is old:
                self.t1.refresh_from_db(); self.assertEqual(self.t1.status, "OCCUPIED")
        self.t1.refresh_from_db(); self.assertEqual(self.t1.status, "AVAILABLE")

    def test_cannot_leave_the_original_empty(self):
        r = self.split([{"item": self.items["Burger"], "quantity": 3}, {"item": self.items["Fries"], "quantity": 2}])
        self.assertEqual(r.status_code, 400)

    def test_bad_quantities_and_foreign_items_are_refused(self):
        self.assertEqual(self.split([{"item": self.items["Burger"], "quantity": 9}]).status_code, 400)
        self.assertEqual(self.split([{"item": self.items["Burger"], "quantity": 0}]).status_code, 400)
        self.assertEqual(self.split([{"item": 99999, "quantity": 1}]).status_code, 400)
        self.assertEqual(self.split([]).status_code, 400)
        self.assertEqual(Order.objects.count(), 1)

    def test_refused_after_a_payment_was_taken(self):
        self.open_shift(self.a, self.loc_a)
        self.pay(self.a, self.o["id"], amount=100)
        self.assertEqual(self.split([{"item": self.items["Fries"], "quantity": 1}]).status_code, 400)

    def test_deal_lines_cannot_be_split(self):
        from apps.orders.models import OrderItem
        OrderItem.objects.filter(pk=self.items["Fries"]).update(deal_name="Combo", deal=None)
        from apps.catalog.models import Deal
        from django.utils import timezone
        from datetime import timedelta
        d = Deal.objects.create(organization=self.org_a, name="Combo", slug="c", discount_type="FIXED", discount_value=10, start_at=timezone.now() - timedelta(days=1), end_at=timezone.now() + timedelta(days=1))
        OrderItem.objects.filter(pk=self.items["Fries"]).update(deal=d)
        self.assertEqual(self.split([{"item": self.items["Fries"], "quantity": 1}]).status_code, 400)

    def test_other_restaurant_cannot_split(self):
        self.assertEqual(self.b.post(f"/api/v1/orders/{self.o['id']}/split/", {"items": [{"item": self.items["Fries"], "quantity": 1}]}, format="json").status_code, 404)


from tests.test_inventory import InventoryBase


class SplitKeepsStockRight(_NoTax, InventoryBase):
    def test_splitting_does_not_change_what_was_consumed(self):
        from apps.orders.models import Table
        t = Table.objects.create(location=self.loc_a, table_number="T-1", capacity=4)
        body = {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id, "order_type": "DINE_IN", "table": t.id,
                "items": [{"product_variant": self.variant_a.id, "quantity": 6}]}
        o = self.a.post(SYNC, body, format="json").json()["order"]
        buns_after_order = self.qty(self.bun)
        cheese_after_order = self.qty(self.cheese)
        r = self.a.post(f"/api/v1/orders/{o['id']}/split/", {"items": [{"item": o["items"][0]["id"], "quantity": 2}]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual((self.qty(self.bun), self.qty(self.cheese)), (buns_after_order, cheese_after_order))


class OptionManagementApi(TenantTestCase):
    """The Setup → Dish options screen: create group, options, attach to a dish."""
    def test_owner_builds_options_for_a_dish(self):
        c = self.a
        g = c.post('/api/v1/catalog/modifier-groups/', {'name': 'Spice', 'is_required': True, 'min_selections': 1, 'max_selections': 1}, format='json')
        self.assertEqual(g.status_code, 201, g.content)
        for i, n in enumerate(['Mild', 'Hot']):
            o = c.post('/api/v1/catalog/modifier-options/', {'modifier_group': g.data['id'], 'name': n, 'price_adjustment': '0', 'position': i}, format='json')
            self.assertEqual(o.status_code, 201, o.content)
        link = c.post('/api/v1/catalog/product-modifier-groups/', {'product': self.variant_a.product_id, 'modifier_group': g.data['id']}, format='json')
        self.assertEqual(link.status_code, 201, link.content)
        p = c.get(f'/api/v1/catalog/products/{self.variant_a.product_id}/').data
        self.assertEqual([x['name'] for x in p['modifier_groups'][0]['options']], ['Mild', 'Hot'])
