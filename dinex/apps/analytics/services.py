"""
Restaurant analytics. Everything is computed from data the system already has (orders, payments, recipes, stock
movements, attendance, payroll, customers): nothing is typed in twice. Money is cash-basis like the sales report:
a sale counts on the day it was paid.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Max, Min, Q, Sum
from django.db.models.functions import ExtractHour, ExtractIsoWeekDay
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.models import Payment
from apps.catalog.models import ProductVariant
from apps.customers.models import Customer
from apps.inventory import services as inv
from apps.inventory.models import Ingredient, IngredientStock, MovementType, StockMovement
from apps.orders.models import Order, OrderItem
from apps.staff import attendance as att
from apps.staff.models import Employee, RiderSettlement

ZERO = Decimal("0.00")


def pct_change(cur, prev):
    cur, prev = Decimal(str(cur or 0)), Decimal(str(prev or 0))
    if prev == 0:
        return None if cur == 0 else None        # nothing to compare with
    return float(((cur - prev) / prev * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def previous_period(start, end):
    days = (end - start).days + 1
    pe = start - timedelta(days=1)
    return pe - timedelta(days=days - 1), pe


def paid_orders(locations, start, end):
    """Orders that took money in the period and were not cancelled."""
    ids = Payment.objects.filter(shift__location__in=locations, kind="PAYMENT", created_at__date__range=(start, end)).values("order_id")
    return Order.objects.filter(id__in=ids).exclude(status="CANCELLED")


# ───────────────────────── overview ─────────────────────────
KPIS = [("net_sales", "Net sales"), ("orders", "Orders"), ("average_order", "Average order"), ("food_cost", "Food cost"),
        ("food_profit", "Food profit"), ("discounts", "Discounts"), ("refunds", "Refunds")]


def overview(locations, start, end):
    cur = cash.sales_report(locations, start, end)
    ps, pe = previous_period(start, end)
    prev = cash.sales_report(locations, ps, pe)

    def created(a, b):
        qs = Order.objects.filter(location__in=locations, created_at__date__range=(a, b))
        return qs.count(), qs.filter(status="CANCELLED").count()

    n_cur, c_cur = created(start, end)
    n_prev, c_prev = created(ps, pe)
    net_ex = lambda s: s["net_sales"] - s["tax"] - s["service_charge"]
    kpis = {}
    for key, label in KPIS:
        a, b = cur["summary"][key], prev["summary"][key]
        kpis[key] = {"label": label, "value": a, "previous": b, "change": pct_change(a, b)}
    kpis["cancel_rate"] = {"label": "Cancelled orders", "value": round(c_cur / n_cur * 100, 1) if n_cur else 0.0, "previous": round(c_prev / n_prev * 100, 1) if n_prev else 0.0,
                           "change": None, "count": c_cur, "of": n_cur}
    ex = net_ex(cur["summary"])
    kpis["food_cost_pct"] = {"label": "Food cost %", "value": round(float(cur["summary"]["food_cost"] / ex * 100), 1) if ex > 0 else None,
                             "previous": None, "change": None}

    by_day = {r["date"]: r["net"] for r in cur["by_day"]}
    series, d = [], start
    while d <= end:
        series.append({"date": d, "net": by_day.get(d, ZERO)})
        d += timedelta(days=1)
    prev_by_day = {r["date"]: r["net"] for r in prev["by_day"]}
    prev_series, d = [], ps
    while d <= pe:
        prev_series.append({"date": d, "net": prev_by_day.get(d, ZERO)})
        d += timedelta(days=1)

    channels = {k: {"orders": 0, "sales": ZERO} for k in ("DINE_IN", "TAKEAWAY", "DELIVERY")}
    for r in paid_orders(locations, start, end).values("order_type").annotate(n=Count("id"), sales=Sum("total_amount")):
        channels[r["order_type"]] = {"orders": r["n"], "sales": r["sales"] or ZERO}
    for c in channels.values():
        c["average"] = (c["sales"] / c["orders"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if c["orders"] else ZERO

    heat = [[0] * 24 for _ in range(7)]
    rows = (Order.objects.filter(location__in=locations, created_at__date__range=(start, end)).exclude(status="CANCELLED")
            .annotate(dow=ExtractIsoWeekDay("created_at"), hr=ExtractHour("created_at")).values("dow", "hr").annotate(n=Count("id")))
    for r in rows:
        heat[r["dow"] - 1][r["hr"]] += r["n"]
    flat = [(heat[d][h], d, h) for d in range(7) for h in range(24)]
    best = max(flat) if any(x[0] for x in flat) else None
    weekday_totals = [sum(heat[d]) for d in range(7)]
    best_day = max(range(7), key=lambda d: weekday_totals[d]) if any(weekday_totals) else None

    return {
        "from": start, "to": end, "previous": {"from": ps, "to": pe}, "kpis": kpis, "series": series, "previous_series": prev_series,
        "by_method": cur["by_method"], "channels": channels, "heatmap": heat, "weekday_orders": weekday_totals,
        "busiest": {"weekday": best[1] if best else None, "hour": best[2] if best else None, "orders": best[0] if best else 0},
        "best_weekday": best_day,
    }


# ───────────────────────── menu engineering ─────────────────────────
ADVICE = {
    "STAR": "Popular and profitable. Protect it: keep quality and a prominent place on the menu.",
    "PLOWHORSE": "Popular but earns little per plate. Try a small price rise, a smaller portion, or cheaper ingredients.",
    "PUZZLE": "Profitable but few people order it. Promote it: better name, photo, staff suggestions, combos.",
    "DOG": "Neither popular nor profitable. Consider replacing it or reworking it.",
}


def classify(items):
    """
    Menu engineering. items: [{qty, unit_profit}] for dishes with a known cost.
    Popular = sells at least 70% of an equal share of all plates; profitable = earns at least the average per plate.
    Returns the class for each item (same order).
    """
    n = len(items)
    total_qty = sum(i["qty"] for i in items)
    if n == 0 or total_qty == 0:
        return []
    avg_profit = sum(Decimal(str(i["unit_profit"])) * i["qty"] for i in items) / total_qty
    threshold = Decimal("0.7") / n
    out = []
    for i in items:
        popular = Decimal(i["qty"]) / total_qty >= threshold
        profitable = Decimal(str(i["unit_profit"])) >= avg_profit
        out.append("STAR" if popular and profitable else "PLOWHORSE" if popular else "PUZZLE" if profitable else "DOG")
    return out


def menu(locations, start, end):
    orders = paid_orders(locations, start, end)
    rows = list(OrderItem.objects.filter(order__in=orders, is_deleted=False).values("product_variant_id", "product_name", "variant_name")
                .annotate(qty=Sum("quantity"), revenue=Sum("total_price")).order_by("-revenue"))
    variants = ProductVariant.objects.filter(id__in=[r["product_variant_id"] for r in rows if r["product_variant_id"]]).select_related("product__category")
    vmap = {v.id: v for v in variants}
    items, unknown = [], []
    for r in rows:
        v = vmap.get(r["product_variant_id"])
        recipe = inv._recipe_of(v) if v else None
        unit_cost = inv.recipe_cost_per_output(recipe) if recipe else None
        qty, revenue = r["qty"], r["revenue"]
        label = r["product_name"] + (f" · {r['variant_name']}" if r["variant_name"] and r["variant_name"] != "Regular" else "")
        item = {"variant": r["product_variant_id"], "name": label, "category": v.product.category.name if v and v.product.category_id else "Other",
                "qty": qty, "revenue": revenue, "unit_price": (revenue / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if qty else ZERO}
        if unit_cost is None:
            item.update(unit_cost=None, cost=None, profit=None, unit_profit=None, margin=None, klass="UNKNOWN", advice="Add a recipe to see how profitable this dish is.")
            unknown.append(item)
        else:
            cost = unit_cost * qty
            item.update(unit_cost=unit_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), cost=cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), profit=(revenue - cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                        unit_profit=(item["unit_price"] - unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                        margin=float(((revenue - cost) / revenue * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) if revenue else None)
            items.append(item)
    for item, k in zip(items, classify([{"qty": i["qty"], "unit_profit": i["unit_profit"]} for i in items])):
        item["klass"], item["advice"] = k, ADVICE[k]
    all_items = items + unknown
    total_qty = sum(i["qty"] for i in all_items) or 1
    for i in all_items:
        i["share"] = round(i["qty"] / total_qty * 100, 1)

    cats = defaultdict(lambda: {"qty": 0, "revenue": ZERO, "profit": ZERO})
    for i in all_items:
        c = cats[i["category"]]
        c["qty"] += i["qty"]; c["revenue"] += i["revenue"]; c["profit"] += i["profit"] or ZERO
    sold_ids = {i["variant"] for i in all_items}
    org_ids = {l.organization_id for l in locations}
    idle = [f"{v.product.name}" + (f" · {v.name}" if v.name != "Regular" else "")
            for v in ProductVariant.objects.filter(product__organization_id__in=org_ids, is_active=True, product__is_active=True).exclude(id__in=sold_ids).select_related("product")[:15]]
    counts = defaultdict(int)
    for i in items:
        counts[i["klass"]] += 1
    return {"from": start, "to": end, "items": all_items, "categories": [{"name": k, **v} for k, v in sorted(cats.items(), key=lambda kv: -kv[1]["revenue"])],
            "counts": dict(counts), "unknown": len(unknown), "not_selling": idle}


# ───────────────────────── staff ─────────────────────────
def labor_cost(locations, start, end):
    """Payroll gross for the period: each month's payslips, pro-rated by the days of that month inside the period."""
    from calendar import monthrange
    from apps.payroll.models import Payslip
    total, d = ZERO, start.replace(day=1)
    while d <= end:
        days = monthrange(d.year, d.month)[1]
        m_end = d.replace(day=days)
        overlap = (min(end, m_end) - max(start, d)).days + 1
        if overlap > 0:
            gross = Payslip.objects.filter(run__location__in=locations, run__month=d).aggregate(t=Sum("gross"))["t"] or ZERO
            total += gross * Decimal(overlap) / Decimal(days)
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def staff(locations, start, end, include_labor):
    at = att.now()
    orders = Order.objects.filter(location__in=locations, created_at__date__range=(start, end)).exclude(status="CANCELLED")
    waiters = []
    for r in orders.filter(waiter__isnull=False).values("waiter_id", "waiter__name").annotate(n=Count("id"), sales=Sum("total_amount")).order_by("-sales"):
        waiters.append({"employee": r["waiter_id"], "name": r["waiter__name"], "orders": r["n"], "sales": r["sales"],
                        "average_bill": (r["sales"] / r["n"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if r["n"] else ZERO})
    riders = []
    delivered = Order.objects.filter(location__in=locations, order_type="DELIVERY", status="COMPLETED", rider__isnull=False, delivered_at__date__range=(start, end))
    short = {r["rider_id"]: r["t"] for r in RiderSettlement.objects.filter(location__in=locations, created_at__date__range=(start, end)).values("rider_id").annotate(t=Sum("shortage"))}
    per = defaultdict(list)
    for o in delivered.select_related("rider"):
        per[o.rider_id].append(o)
    for rid, os_ in per.items():
        mins = [(o.delivered_at - o.dispatched_at).total_seconds() / 60 for o in os_ if o.dispatched_at]
        e = os_[0].rider
        riders.append({"employee": rid, "name": e.name, "deliveries": len(os_), "avg_minutes": round(sum(mins) / len(mins), 1) if mins else None,
                       "slowest_minutes": round(max(mins), 1) if mins else None, "commission": (e.delivery_commission * len(os_)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                       "cash_shortage": short.get(rid, ZERO)})
    riders.sort(key=lambda r: -r["deliveries"])

    sched = present = late_days = absent = overtime = worked = 0
    people = []
    for loc in locations:
        for row in att.report(loc, start, end, None, at):
            e = row["employee"]
            sched += row["scheduled_days"]; present += row["present_days"] - row["off_days_worked"]; late_days += row["late_days"]
            absent += row["absent_days"]; overtime += row["overtime_minutes"]; worked += row["worked_minutes"]
            people.append({"name": e.name, "role": e.get_role_display(), "late_days": row["late_days"], "late_minutes": row["late_minutes"],
                           "absent_days": row["absent_days"], "overtime_minutes": row["overtime_minutes"]})
    attendance = {
        "scheduled_days": sched, "attendance_rate": round(present / sched * 100, 1) if sched else None, "late_rate": round(late_days / present * 100, 1) if present else None,
        "absent_days": absent, "overtime_hours": round(overtime / 60, 1), "hours_worked": round(worked / 60, 1),
        "most_late": sorted([p for p in people if p["late_days"]], key=lambda p: -p["late_days"])[:5],
        "most_overtime": sorted([p for p in people if p["overtime_minutes"]], key=lambda p: -p["overtime_minutes"])[:5],
        "most_absent": sorted([p for p in people if p["absent_days"]], key=lambda p: -p["absent_days"])[:5],
    }
    net = cash.sales_report(locations, start, end)["summary"]["net_sales"]
    labor = None
    if include_labor:
        cost = labor_cost(locations, start, end)
        labor = {"cost": cost, "pct_of_sales": round(float(cost / net * 100), 1) if net > 0 else None,
                 "sales_per_hour": (net / Decimal(worked / 60)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if worked else None}
    return {"from": start, "to": end, "waiters": waiters, "riders": riders, "attendance": attendance, "labor": labor, "net_sales": net}


# ───────────────────────── inventory ─────────────────────────
def inventory(locations, start, end):
    days = max(1, (end - start).days + 1)
    moves = StockMovement.objects.filter(location__in=locations, created_at__date__range=(start, end))
    cost = {i.id: i for i in Ingredient.objects.filter(organization_id__in={l.organization_id for l in locations})}

    def by_type(kind):
        out = defaultdict(lambda: ZERO)
        for r in moves.filter(movement_type=kind).values("ingredient_id").annotate(t=Sum("quantity_change")):
            out[r["ingredient_id"]] += r["t"]
        return out

    sold, reversed_ = by_type(MovementType.SALE), by_type(MovementType.SALE_REVERSAL)
    used = {i: -(sold[i] + reversed_[i]) for i in set(sold) | set(reversed_)}
    waste = {i: -q for i, q in by_type(MovementType.WASTAGE).items()}
    adjust = by_type(MovementType.ADJUSTMENT)
    bought_qty = by_type(MovementType.PURCHASE)
    value = lambda iid, q: (Decimal(q) * cost[iid].cost_per_unit).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    stock = defaultdict(lambda: ZERO)
    for s in IngredientStock.objects.filter(location__in=locations):
        stock[s.ingredient_id] += s.quantity

    top_used = sorted([{"ingredient": i, "name": cost[i].name, "unit": cost[i].base_unit, "quantity": q, "value": value(i, q)} for i, q in used.items() if q > 0], key=lambda r: -r["value"])
    wasted = sorted([{"ingredient": i, "name": cost[i].name, "unit": cost[i].base_unit, "quantity": q, "value": value(i, q)} for i, q in waste.items() if q > 0], key=lambda r: -r["value"])
    losses = sum((value(i, -q) for i, q in adjust.items() if q < 0), ZERO)
    gains = sum((value(i, q) for i, q in adjust.items() if q > 0), ZERO)
    used_value = sum((r["value"] for r in top_used), ZERO)
    waste_value = sum((r["value"] for r in wasted), ZERO)
    cover = []
    for i, q in used.items():
        if q > 0 and cost[i].is_active and not cost[i].is_prepared:
            daily = q / days
            left = stock.get(i, ZERO)
            cover.append({"ingredient": i, "name": cost[i].name, "unit": cost[i].base_unit, "in_stock": left, "daily_use": daily.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                          "days_left": float((left / daily).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) if daily else None})
    cover.sort(key=lambda r: (r["days_left"] is None, r["days_left"]))
    return {
        "from": start, "to": end,
        "totals": {"used_value": used_value, "wastage_value": waste_value, "wastage_pct": round(float(waste_value / used_value * 100), 1) if used_value > 0 else None,
                   "count_losses": losses, "count_gains": gains,
                   "purchases_value": sum((value(i, q) for i, q in bought_qty.items() if q > 0), ZERO),
                   "stock_value": sum((value(i, q) for i, q in stock.items() if q > 0), ZERO)},
        "top_used": top_used[:10], "top_wasted": wasted[:10], "running_out": [c for c in cover if c["days_left"] is not None and c["days_left"] < 3][:10], "cover": cover[:15],
    }


# ───────────────────────── customers ─────────────────────────
def customers(locations, start, end):
    orders = paid_orders(locations, start, end)
    with_customer = orders.filter(customer__isnull=False)
    active = with_customer.values("customer_id").annotate(n=Count("id"), spent=Sum("total_amount"), first_here=Min("created_at"))
    ids = [r["customer_id"] for r in active]
    firsts = {r["customer_id"]: r["f"] for r in Order.objects.filter(customer_id__in=ids).exclude(status="CANCELLED").values("customer_id").annotate(f=Min("created_at"))}
    new = returning = 0
    for r in active:
        if att.local_date(firsts[r["customer_id"]]) >= start:
            new += 1
        else:
            returning += 1
    n_active = new + returning
    total_orders = orders.count()
    top = []
    names = {c.id: c for c in Customer.objects.filter(id__in=ids)}
    for r in sorted(active, key=lambda r: -(r["spent"] or 0))[:10]:
        c = names[r["customer_id"]]
        top.append({"customer": c.id, "name": c.full_name, "phone": c.phone, "orders": r["n"], "spent": r["spent"] or ZERO,
                    "average": ((r["spent"] or ZERO) / r["n"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)})
    repeat_orders = sum(r["n"] for r in active if r["n"] > 1)
    return {"from": start, "to": end, "active": n_active, "new": new, "returning": returning,
            "repeat_rate": round(returning / n_active * 100, 1) if n_active else None,
            "orders_with_customer": with_customer.count(), "orders_total": total_orders,
            "identified_pct": round(with_customer.count() / total_orders * 100, 1) if total_orders else None,
            "orders_per_customer": round(with_customer.count() / n_active, 2) if n_active else None, "top": top,
            "repeat_visit_orders": repeat_orders}
