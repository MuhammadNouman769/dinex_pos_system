"""Recipe-based inventory: selling 10 burgers must consume buns, patties, sauce, cheese..."""
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.inventory.models import IngredientStock, StockMovement, Ingredient
from apps.orders.models import Order
from tests.base import TenantTestCase, PASSWORD


class InventoryBase(TenantTestCase):
    def ing(self, client, name, unit, **extra):
        r = client.post("/api/v1/inventory/ingredients/", {"name": name, "base_unit": unit, **extra}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["id"]

    def stock_in(self, client, loc, ingredient, qty, unit="", cost=None, kind="PURCHASE"):
        body = {"location": loc.id, "ingredient": ingredient, "movement_type": kind, "quantity": str(qty), "unit": unit}
        if cost is not None:
            body["unit_cost"] = str(cost)
        r = client.post("/api/v1/inventory/stock/movements/", body, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def qty(self, ingredient, loc=None):
        return IngredientStock.objects.get(ingredient_id=ingredient, location=loc or self.loc_a).quantity

    def setUp(self):
        a = self.a
        self.chicken = self.ing(a, "Chicken mince", "G", cost_per_unit="0.9")
        self.crumbs = self.ing(a, "Breadcrumbs", "G")
        self.bun = self.ing(a, "Bun", "PCS")
        self.sauce = self.ing(a, "Sauce", "ML")
        self.cheese = self.ing(a, "Cheese slice", "PCS")
        self.patty = self.ing(a, "Chicken patty", "PCS", is_prepared=True)

        # patty (1 pc) = 100 g chicken + 10 g breadcrumbs
        r = a.put(f"/api/v1/inventory/recipes/ingredient/{self.patty}/", {"output_quantity": "1", "lines": [
            {"ingredient": self.chicken, "quantity": "100", "unit": "g"},
            {"ingredient": self.crumbs, "quantity": "10", "unit": "g"}]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        # burger = 1 bun + 1 patty + 20 ml sauce + 1 cheese
        r = a.put(f"/api/v1/inventory/recipes/variant/{self.variant_a.id}/", {"lines": [
            {"ingredient": self.bun, "quantity": "1"},
            {"ingredient": self.patty, "quantity": "1"},
            {"ingredient": self.sauce, "quantity": "20", "unit": "ml"},
            {"ingredient": self.cheese, "quantity": "1"}]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.recipe = r.json()

        self.stock_in(a, self.loc_a, self.chicken, 5, "kg", cost=900)   # Rs 900 per kg
        self.stock_in(a, self.loc_a, self.crumbs, 1, "kg")
        self.stock_in(a, self.loc_a, self.bun, 2, "dozen")
        self.stock_in(a, self.loc_a, self.sauce, 1, "l")
        self.stock_in(a, self.loc_a, self.cheese, 30, "pcs")

    def order_with_burgers(self, n=10, client=None):
        client = client or self.a
        o = self.new_order(client, self.loc_a)
        self.assertEqual(self.add_item(client, o["id"], self.variant_a, n).status_code, 201)
        return o

    def set_status(self, order, st, client=None):
        return (client or self.a).post(f"/api/v1/orders/{order['id']}/status/",
                                       {"status": st, "reason": "customer changed mind"}, format="json")


class UnitsAndLedger(InventoryBase):
    def test_units_are_converted_to_base(self):
        self.assertEqual(self.qty(self.chicken), Decimal("5000"))      # 5 kg -> g
        self.assertEqual(self.qty(self.bun), Decimal("24"))            # 2 dozen
        self.assertEqual(self.qty(self.sauce), Decimal("1000"))        # 1 l -> ml

    def test_wrong_unit_for_ingredient_is_rejected(self):
        r = self.a.post("/api/v1/inventory/stock/movements/", {
            "location": self.loc_a.id, "ingredient": self.chicken, "movement_type": "PURCHASE",
            "quantity": "1", "unit": "l"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_weighted_average_cost_and_ledger(self):
        # 5000 g at Rs 0.9/g on hand; buy 5 kg more at Rs 1100/kg -> avg 1.0/g
        self.stock_in(self.a, self.loc_a, self.chicken, 5, "kg", cost=1100)
        self.assertEqual(Ingredient.objects.get(pk=self.chicken).cost_per_unit, Decimal("1.0000"))
        moves = StockMovement.objects.filter(ingredient_id=self.chicken)
        self.assertEqual(moves.count(), 2)
        self.assertEqual(moves.first().balance_after, Decimal("10000"))

    def test_wastage_and_adjustment(self):
        self.stock_in(self.a, self.loc_a, self.cheese, 4, "pcs", kind="WASTAGE")
        self.assertEqual(self.qty(self.cheese), 26)
        self.stock_in(self.a, self.loc_a, self.cheese, -1, "pcs", kind="ADJUSTMENT")
        self.assertEqual(self.qty(self.cheese), 25)

    def test_low_stock_flag(self):
        self.a.patch(f"/api/v1/inventory/ingredients/{self.cheese}/", {"reorder_level": "40"}, format="json")
        r = self.a.get(f"/api/v1/inventory/stock/?location={self.loc_a.id}&low=true")
        self.assertEqual([x["ingredient_name"] for x in r.json()["results"]], ["Cheese slice"])


class RecipesAndCost(InventoryBase):
    def test_cost_and_margin_include_sub_recipe(self):
        # patty = 100*0.9 = 90 ; burger = patty 90 (bun, sauce, cheese have no cost) -> 90
        self.assertEqual(Decimal(self.recipe["cost"]), Decimal("90.00"))
        self.assertEqual(Decimal(self.recipe["profit"]), Decimal("410.00"))   # price 500

    def test_preparation_cannot_use_itself(self):
        r = self.a.put(f"/api/v1/inventory/recipes/ingredient/{self.patty}/", {"lines": [
            {"ingredient": self.patty, "quantity": "1"}]}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cannot_delete_ingredient_used_in_recipe(self):
        self.assertEqual(self.a.delete(f"/api/v1/inventory/ingredients/{self.bun}/").status_code, 400)

    def test_base_unit_cannot_change(self):
        r = self.a.patch(f"/api/v1/inventory/ingredients/{self.bun}/", {"base_unit": "G"}, format="json")
        self.assertEqual(r.status_code, 400)


class SellingDeductsIngredients(InventoryBase):
    def test_ten_burgers_consume_everything_in_the_recipe(self):
        o = self.order_with_burgers(10)
        # nothing is used while the order is only PENDING
        self.assertEqual(self.qty(self.bun), 24)
        self.assertEqual(self.set_status(o, "CONFIRMED").status_code, 200)
        self.assertEqual(self.qty(self.bun), 14)
        self.assertEqual(self.qty(self.cheese), 20)
        self.assertEqual(self.qty(self.sauce), 800)          # 10 x 20 ml
        self.assertEqual(self.qty(self.chicken), 4000)       # 10 patties x 100 g
        self.assertEqual(self.qty(self.crumbs), 900)         # 10 patties x 10 g
        self.assertFalse(IngredientStock.objects.filter(ingredient_id=self.patty).exists())

    def test_cancel_before_cooking_returns_stock(self):
        o = self.order_with_burgers(10)
        self.set_status(o, "CONFIRMED")
        self.assertEqual(self.set_status(o, "CANCELLED").status_code, 200)
        self.assertEqual(self.qty(self.chicken), 5000)
        self.assertEqual(self.qty(self.bun), 24)
        kinds = set(StockMovement.objects.filter(reference_id=o["id"]).values_list("movement_type", flat=True))
        self.assertEqual(kinds, {"SALE", "SALE_REVERSAL"})

    def test_cancel_after_cooking_started_keeps_stock_used(self):
        o = self.order_with_burgers(10)
        self.set_status(o, "CONFIRMED")
        self.set_status(o, "PREPARING")
        self.set_status(o, "CANCELLED")
        self.assertEqual(self.qty(self.bun), 14)

    def test_adding_and_removing_items_after_confirm_moves_only_the_difference(self):
        o = self.order_with_burgers(10)
        self.set_status(o, "CONFIRMED")
        extra = self.add_item(self.a, o["id"], self.variant_a, 5).json()
        self.assertEqual(self.qty(self.bun), 9)
        self.assertEqual(self.a.delete(f"/api/v1/orders/items/{extra['id']}/").status_code, 204)
        self.assertEqual(self.qty(self.bun), 14)
        item = o and self.a.get(f"/api/v1/orders/{o['id']}/").json()
        first = Order.objects.get(pk=o["id"]).items.first()
        self.a.patch(f"/api/v1/orders/items/{first.id}/", {"quantity": 4}, format="json")
        self.assertEqual(self.qty(self.bun), 20)

    def test_items_without_recipe_do_not_touch_stock(self):
        from apps.catalog.models import ProductVariant
        plain = ProductVariant.objects.create(product=self.variant_a.product, name="Water", base_price=50)
        o = self.new_order(self.a, self.loc_a)
        self.add_item(self.a, o["id"], plain, 3)
        self.assertEqual(self.set_status(o, "CONFIRMED").status_code, 200)
        self.assertEqual(self.qty(self.bun), 24)

    def test_block_policy_stops_the_sale_and_changes_nothing(self):
        self.loc_a.inventory_policy = "BLOCK"
        self.loc_a.save()
        o = self.order_with_burgers(30)                     # only 24 buns
        r = self.set_status(o, "CONFIRMED")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Bun", r.json()["error"])
        self.assertEqual(Order.objects.get(pk=o["id"]).status, "PENDING")
        self.assertEqual(self.qty(self.bun), 24)
        self.assertEqual(self.qty(self.chicken), 5000)

    def test_block_policy_rolls_back_an_item_added_after_confirm(self):
        self.loc_a.inventory_policy = "BLOCK"
        self.loc_a.save()
        o = self.order_with_burgers(10)
        self.set_status(o, "CONFIRMED")
        r = self.add_item(self.a, o["id"], self.variant_a, 50)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Order.objects.get(pk=o["id"]).items.count(), 1)
        self.assertEqual(self.qty(self.bun), 14)

    def test_allow_policy_lets_stock_go_negative_and_warn_reports_it(self):
        o = self.order_with_burgers(30)
        self.assertEqual(self.set_status(o, "CONFIRMED").status_code, 200)
        self.assertEqual(self.qty(self.bun), -6)
        self.loc_a.inventory_policy = "WARN"
        self.loc_a.save()
        o2 = self.order_with_burgers(1)
        r = self.set_status(o2, "CONFIRMED")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["stock_warnings"])

    def test_deleting_an_open_order_returns_stock(self):
        o = self.order_with_burgers(10)
        self.set_status(o, "CONFIRMED")
        self.assertEqual(self.a.delete(f"/api/v1/orders/{o['id']}/").status_code, 204)
        self.assertEqual(self.qty(self.bun), 24)


class InventoryAccess(InventoryBase):
    def staff(self, role, username):
        r = self.a.post("/api/v1/organizations/location-staff/", {
            "username": username, "email": f"{username}@x.com", "password": PASSWORD, "first_name": "S",
            "last_name": "T", "location_id": self.loc_a.id, "role": role}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return self.as_user(get_user_model().objects.get(username=username))

    def test_other_restaurant_cannot_see_or_use_my_ingredients(self):
        self.assertEqual(self.b.get(f"/api/v1/inventory/ingredients/{self.bun}/").status_code, 404)
        names = [i["name"] for i in self.b.get("/api/v1/inventory/ingredients/").json()["results"]]
        self.assertEqual(names, [])
        r = self.b.post("/api/v1/inventory/stock/movements/", {
            "location": self.loc_b.id, "ingredient": self.bun, "movement_type": "PURCHASE", "quantity": "5"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.b.put(f"/api/v1/inventory/recipes/variant/{self.variant_a.id}/", {"lines": [
            {"ingredient": self.bun, "quantity": "1"}]}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_cashier_reads_but_cannot_change_stock_or_recipes(self):
        cashier = self.staff("POS_OPERATOR", "cash1")
        self.assertEqual(cashier.get("/api/v1/inventory/stock/").status_code, 200)
        r = cashier.post("/api/v1/inventory/stock/movements/", {
            "location": self.loc_a.id, "ingredient": self.bun, "movement_type": "WASTAGE", "quantity": "1"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(cashier.post("/api/v1/inventory/ingredients/", {"name": "X", "base_unit": "G"}, format="json").status_code, 403)

    def test_manager_can_adjust_stock_only_at_own_location(self):
        from apps.organizations.models import Location
        other = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123")
        manager = self.staff("MANAGER", "mgr1")
        r = manager.post("/api/v1/inventory/stock/movements/", {
            "location": self.loc_a.id, "ingredient": self.bun, "movement_type": "WASTAGE", "quantity": "1"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        r = manager.post("/api/v1/inventory/stock/movements/", {
            "location": other.id, "ingredient": self.bun, "movement_type": "WASTAGE", "quantity": "1"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_bad_params_are_400(self):
        self.assertEqual(self.a.get("/api/v1/inventory/stock/?location=abc").status_code, 400)
        self.assertEqual(self.a.get("/api/v1/inventory/stock/movements/?ingredient=abc").status_code, 400)


class FloorsAndSettings(TenantTestCase):
    def test_floors_crud_and_rules(self):
        r = self.a.post("/api/v1/orders/floors/", {"location": self.loc_a.id, "name": "Basement", "level": -1}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        base = r.json()["id"]
        ground = self.a.post("/api/v1/orders/floors/", {"location": self.loc_a.id, "name": "Ground Floor", "level": 0}, format="json").json()["id"]
        self.assertEqual(self.a.post("/api/v1/orders/floors/", {"location": self.loc_a.id, "name": "basement"}, format="json").status_code, 400)
        names = [f["name"] for f in self.a.get("/api/v1/orders/floors/").json()["results"]]
        self.assertEqual(names, ["Basement", "Ground Floor"])               # ordered by level
        t = self.a.post("/api/v1/orders/tables/", {"location": self.loc_a.id, "floor": ground, "table_number": "T-1"}, format="json")
        self.assertEqual(t.status_code, 201, t.content)
        self.assertEqual(t.json()["floor_name"], "Ground Floor")
        self.assertEqual(self.a.delete(f"/api/v1/orders/floors/{ground}/").status_code, 400)   # has tables
        self.assertEqual(self.a.delete(f"/api/v1/orders/floors/{base}/").status_code, 204)
        self.assertEqual(self.a.post("/api/v1/orders/floors/", {"location": self.loc_a.id, "name": "Basement"}, format="json").status_code, 201)

    def test_floor_isolation(self):
        fb = self.b.post("/api/v1/orders/floors/", {"location": self.loc_b.id, "name": "Ground"}, format="json").json()["id"]
        self.assertEqual(self.a.get(f"/api/v1/orders/floors/{fb}/").status_code, 404)
        r = self.a.post("/api/v1/orders/tables/", {"location": self.loc_a.id, "floor": fb, "table_number": "T-1"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.a.post("/api/v1/orders/floors/", {"location": self.loc_b.id, "name": "Hack"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_tax_and_service_charge_come_from_location_settings(self):
        r = self.a.patch(f"/api/v1/organizations/locations/{self.loc_a.id}/",
                         {"tax_rate": "16", "service_charge_rate": "5"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        o = self.new_order(self.a, self.loc_a)
        self.add_item(self.a, o["id"], self.variant_a, 2)                    # subtotal 1000
        d = self.a.get(f"/api/v1/orders/{o['id']}/").json()
        self.assertEqual(Decimal(d["tax"]), Decimal("160.00"))
        self.assertEqual(Decimal(d["service_charge"]), Decimal("50.00"))
        self.assertEqual(Decimal(d["total_amount"]), Decimal("1210.00"))
