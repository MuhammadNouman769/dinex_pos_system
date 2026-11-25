"""
Cash & sales logic: payments, refunds, shifts, Z-report, sales report.

Rules
- Money only moves through Payment rows (kind PAYMENT / REFUND) that belong to an open Shift.
  An order's payment_status is *derived* from those rows, never typed in by a client.
- Expected cash in the drawer =
      opening + cash sales - cash refunds + cash in - cash out - expenses - safe drops
- Everything here is append-only: corrections are new rows, with an AuditLog entry.
"""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.cash.models import AuditLog, CashMovement, Payment, PaymentMethod, Shift

ZERO = Decimal("0.00")
CENTS = Decimal("0.01")
ORDER_METHOD = {"CASH": "CASH", "CARD": "CARD", "WALLET": "ONLINE", "BANK": "ONLINE"}


class CashError(APIException):
    status_code = 400
    default_code = "cash_error"


def q2(value):
    return Decimal(str(value)).quantize(CENTS)


def _json_safe(d):
    """Audit details are stored as JSON: anything that is not plain JSON (Decimal, date, datetime…) becomes text."""
    plain = (str, int, float, bool, list, dict, type(None))
    return {k: (v if isinstance(v, plain) else str(v)) for k, v in d.items()}


def audit(user, location, action, obj=None, **details):
    return AuditLog.objects.create(
        organization_id=location.organization_id, location=location,
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        object_type=type(obj).__name__ if obj is not None else "",
        object_id=getattr(obj, "pk", None),
        details=_json_safe(details),
    )


# ───────────────────────── payments ─────────────────────────
def paid_and_refunded(order, method=None):
    qs = order.payments.all()
    if method:
        qs = qs.filter(method=method)
    agg = qs.aggregate(paid=Sum("amount", filter=Q(kind="PAYMENT")), refunded=Sum("amount", filter=Q(kind="REFUND")))
    return agg["paid"] or ZERO, agg["refunded"] or ZERO


def sync_payment_status(order):
    """Derive order.payment_status from its payment rows."""
    paid, refunded = paid_and_refunded(order)
    if paid == 0:
        status = "PENDING"
    elif refunded > 0 and paid - refunded <= 0:
        status = "REFUNDED"
    elif paid >= order.total_amount:
        status = "PAID"          # a part-refund (goodwill / complaint) does not make the bill unpaid again
    else:
        status = "PARTIAL"
    type(order).objects.filter(pk=order.pk).update(payment_status=status)
    order.payment_status = status
    if status in ("PAID", "REFUNDED") and order.customer_id:
        try:                                    # points must never get in the way of taking money
            from apps.loyalty import services as loyalty
            loyalty.earn_for_order(order) if status == "PAID" else loyalty.reverse_for_order(order)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("loyalty update failed for order %s", order.pk)
    return status


def amount_due(order):
    """What the customer still owes. Refunds are money given back, they do not reopen the bill."""
    paid, _ = paid_and_refunded(order)
    return order.total_amount - paid


def current_shift(user, location_id):
    return Shift.objects.filter(opened_by=user, location_id=location_id, status=Shift.Status.OPEN).first()


def shift_at(user, location_id, when):
    """The shift this user had open at `when` (used for payments taken offline and synced later)."""
    return (Shift.objects.filter(opened_by=user, location_id=location_id, opened_at__lte=when)
            .filter(Q(closed_at__isnull=True) | Q(closed_at__gte=when)).order_by("-opened_at").first())


@transaction.atomic
def take_payment(order, user, method, amount, tendered=None, reference="", shift=None, at=None):
    from apps.orders.models import Order

    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == "CANCELLED":
        raise CashError("A cancelled order cannot be paid.")
    if method not in PaymentMethod.values:
        raise CashError(f"Payment method must be one of: {', '.join(PaymentMethod.values)}.")
    if order.total_amount <= 0:
        raise CashError("This order has nothing to pay yet. Add items first.")
    amount = q2(amount)
    if amount <= 0:
        raise CashError("Amount must be greater than zero.")
    due = amount_due(order)
    if due <= 0:
        raise CashError("This order is already fully paid.")
    if amount > due:
        raise CashError(f"Amount is more than the balance due ({due}).")
    shift = shift or current_shift(user, order.location_id)
    if shift is None:
        raise CashError("Open your shift before taking payments.")

    tendered_value = None
    if method == PaymentMethod.CASH and tendered not in (None, ""):
        tendered_value = q2(tendered)
        if tendered_value < amount:
            raise CashError("Cash received is less than the amount.")

    payment = Payment.objects.create(
        order=order, shift=shift, kind=Payment.Kind.PAYMENT, method=method, amount=amount,
        tendered=tendered_value, reference=reference[:100], created_by=user,
    )
    if at is not None:
        Payment.objects.filter(pk=payment.pk).update(created_at=at)
    sync_payment_status(order)
    Order.objects.filter(pk=order.pk).update(payment_method=ORDER_METHOD[method])
    return payment, order


@transaction.atomic
def refund_payment(order, user, method, amount, reason):
    from apps.orders.models import Order

    order = Order.objects.select_for_update().get(pk=order.pk)
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise CashError("A reason is required for a refund.")
    if method not in PaymentMethod.values:
        raise CashError(f"Payment method must be one of: {', '.join(PaymentMethod.values)}.")
    amount = q2(amount)
    if amount <= 0:
        raise CashError("Amount must be greater than zero.")
    paid, refunded = paid_and_refunded(order, method)
    if amount > paid - refunded:
        raise CashError(f"Only {paid - refunded} was paid by {method.lower()} and can be refunded this way.")
    shift = current_shift(user, order.location_id)
    if shift is None:
        raise CashError("Open your shift before giving a refund.")

    payment = Payment.objects.create(
        order=order, shift=shift, kind=Payment.Kind.REFUND, method=method, amount=amount,
        reason=reason[:255], created_by=user,
    )
    sync_payment_status(order)
    audit(user, order.location, "refund", order, order_number=order.order_number,
          amount=amount, method=method, reason=reason)
    return payment, order


# ───────────────────────── shifts ─────────────────────────
def _sum(qs, field="amount"):
    return qs.aggregate(t=Sum(field))["t"] or ZERO


def shift_summary(shift):
    """Everything the cashier / owner needs to see for one shift (live while open, final once closed)."""
    from apps.orders.models import Order

    pay = shift.payments.all()
    methods = {}
    for m in PaymentMethod.values:
        sales = _sum(pay.filter(kind="PAYMENT", method=m))
        refunds = _sum(pay.filter(kind="REFUND", method=m))
        methods[m] = {"sales": sales, "refunds": refunds, "net": sales - refunds}

    mov = shift.movements.all()
    cash_in = _sum(mov.filter(kind="CASH_IN"))
    cash_out = _sum(mov.filter(kind="CASH_OUT"))
    expenses = _sum(mov.filter(kind="EXPENSE"))
    safe_drops = _sum(mov.filter(kind="SAFE_DROP"))
    expected = (shift.opening_cash + methods["CASH"]["sales"] - methods["CASH"]["refunds"]
                + cash_in - cash_out - expenses - safe_drops)

    order_ids = list(pay.filter(kind="PAYMENT").values_list("order_id", flat=True).distinct())
    orders = Order.objects.filter(id__in=order_ids)
    totals = orders.aggregate(discount=Sum("discount"), tax=Sum("tax"), service=Sum("service_charge"))

    end = shift.closed_at or timezone.now()
    cancelled = Order.objects.filter(
        location_id=shift.location_id, status="CANCELLED", cancelled_by_id=shift.opened_by_id,
        cancelled_at__gte=shift.opened_at, cancelled_at__lte=end,
    )
    return {
        "id": shift.id, "status": shift.status, "location": shift.location_id, "location_name": shift.location.name,
        "cashier": shift.opened_by.get_full_name() or shift.opened_by.username,
        "opened_at": shift.opened_at, "closed_at": shift.closed_at, "note": shift.note,
        "opening_cash": shift.opening_cash,
        "methods": methods,
        "sales_total": sum((v["sales"] for v in methods.values()), ZERO),
        "refunds_total": sum((v["refunds"] for v in methods.values()), ZERO),
        "net_total": sum((v["net"] for v in methods.values()), ZERO),
        "orders_paid": len(order_ids),
        "discounts": totals["discount"] or ZERO, "tax": totals["tax"] or ZERO, "service_charge": totals["service"] or ZERO,
        "cash_in": cash_in, "cash_out": cash_out, "expenses": expenses, "safe_drops": safe_drops,
        "expected_cash": expected if shift.status == "OPEN" else (shift.expected_cash if shift.expected_cash is not None else expected),
        "counted_cash": shift.counted_cash, "difference": shift.difference,
        "cancelled": {
            "count": cancelled.count(), "total": _sum(cancelled, "total_amount"),
            "orders": [{"order_number": o.order_number, "total": o.total_amount, "reason": o.cancel_reason} for o in cancelled[:20]],
        },
        "movements": [{"id": m.id, "kind": m.kind, "amount": m.amount, "category": m.category,
                       "reason": m.reason, "created_at": m.created_at} for m in mov],
    }


@transaction.atomic
def open_shift(user, location, opening_cash):
    opening_cash = q2(opening_cash)
    if opening_cash < 0:
        raise CashError("Opening cash cannot be negative.")
    if current_shift(user, location.id):
        raise CashError("You already have an open shift at this location.")
    shift = Shift.objects.create(location=location, opened_by=user, opening_cash=opening_cash)
    audit(user, location, "shift_opened", shift, opening_cash=opening_cash)
    return shift


@transaction.atomic
def close_shift(shift, user, counted_cash, note=""):
    shift = Shift.objects.select_for_update().get(pk=shift.pk)
    if shift.status != Shift.Status.OPEN:
        raise CashError("This shift is already closed.")
    counted = q2(counted_cash)
    if counted < 0:
        raise CashError("Counted cash cannot be negative.")
    expected = shift_summary(shift)["expected_cash"]
    shift.status = Shift.Status.CLOSED
    shift.closed_by = user
    shift.closed_at = timezone.now()
    shift.expected_cash = expected
    shift.counted_cash = counted
    shift.difference = counted - expected
    shift.note = (note or "")[:255]
    shift.save()
    audit(user, shift.location, "shift_closed", shift, expected=expected, counted=counted,
          difference=shift.difference)
    return shift


@transaction.atomic
def reopen_shift(shift, user, reason):
    shift = Shift.objects.select_for_update().get(pk=shift.pk)
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise CashError("A reason is required to reopen a shift.")
    if shift.status != Shift.Status.CLOSED:
        raise CashError("This shift is not closed.")
    if current_shift(shift.opened_by, shift.location_id):
        raise CashError("That cashier already has another open shift at this location.")
    shift.status = Shift.Status.OPEN
    shift.closed_by = shift.closed_at = shift.expected_cash = shift.counted_cash = shift.difference = None
    shift.save()
    audit(user, shift.location, "shift_reopened", shift, reason=reason)
    return shift


@transaction.atomic
def add_movement(shift, user, kind, amount, reason="", category=""):
    if shift.status != Shift.Status.OPEN:
        raise CashError("This shift is closed.")
    if kind not in CashMovement.Kind.values:
        raise CashError(f"Kind must be one of: {', '.join(CashMovement.Kind.values)}.")
    amount = q2(amount)
    if amount <= 0:
        raise CashError("Amount must be greater than zero.")
    reason = (reason or "").strip()
    if kind in ("CASH_OUT", "EXPENSE") and len(reason) < 3:
        raise CashError("Please say what the money was for.")
    movement = CashMovement.objects.create(shift=shift, kind=kind, amount=amount, reason=reason[:255],
                                           category=(category or "")[:50], created_by=user)
    if kind in ("CASH_OUT", "EXPENSE") or amount >= 10000:
        audit(user, shift.location, f"cash_{kind.lower()}", movement, amount=amount, reason=reason, category=category)
    return movement


# ───────────────────────── sales report ─────────────────────────
def sales_report(locations, start, end):
    """Owner/manager report for a date range (local dates)."""
    from apps.catalog.models import ProductVariant
    from apps.inventory import services as inv
    from apps.orders.models import Order, OrderItem

    pay = Payment.objects.filter(shift__location__in=locations, created_at__date__gte=start, created_at__date__lte=end)
    sales_qs, refund_qs = pay.filter(kind="PAYMENT"), pay.filter(kind="REFUND")
    gross, refunds = _sum(sales_qs), _sum(refund_qs)
    net = gross - refunds

    by_method = {m: ZERO for m in PaymentMethod.values}
    for row in pay.values("method", "kind").annotate(t=Sum("amount")):
        by_method[row["method"]] += row["t"] if row["kind"] == "PAYMENT" else -row["t"]

    by_day = defaultdict(lambda: ZERO)
    for row in pay.annotate(day=TruncDate("created_at")).values("day", "kind").annotate(t=Sum("amount")):
        by_day[row["day"]] += row["t"] if row["kind"] == "PAYMENT" else -row["t"]
    by_hour = {h: 0 for h in range(24)}
    for row in sales_qs.annotate(hour=ExtractHour("created_at")).values("hour").annotate(n=Count("order", distinct=True)):
        by_hour[row["hour"]] = row["n"]

    orders = Order.objects.filter(id__in=sales_qs.values("order_id")).exclude(status="CANCELLED")
    o_tot = orders.aggregate(n=Count("id"), subtotal=Sum("subtotal"), discount=Sum("discount"),
                             tax=Sum("tax"), service=Sum("service_charge"))
    n_orders = o_tot["n"] or 0

    # items sold, with food cost from recipes
    cost_cache, no_recipe = {}, set()

    def unit_cost(variant_id):
        if variant_id not in cost_cache:
            variant = ProductVariant.objects.filter(pk=variant_id).first()
            recipe = inv._recipe_of(variant) if variant else None
            cost_cache[variant_id] = inv.recipe_cost_per_output(recipe) if recipe else None
        return cost_cache[variant_id]

    items, cogs = [], ZERO
    rows = (OrderItem.objects.filter(order__in=orders, is_deleted=False)
            .values("product_variant_id", "product_name", "variant_name")
            .annotate(qty=Sum("quantity"), revenue=Sum("total_price")).order_by("-revenue"))
    for r in rows:
        c = unit_cost(r["product_variant_id"]) if r["product_variant_id"] else None
        cost = (c * r["qty"]) if c is not None else None
        if c is None:
            no_recipe.add(r["product_name"])
        else:
            cogs += cost
        items.append({"name": r["product_name"], "variant": r["variant_name"], "quantity": r["qty"],
                      "revenue": r["revenue"], "cost": cost.quantize(CENTS) if cost is not None else None,
                      "profit": (r["revenue"] - cost).quantize(CENTS) if cost is not None else None})

    cancelled = Order.objects.filter(location__in=locations, status="CANCELLED",
                                     cancelled_at__date__gte=start, cancelled_at__date__lte=end).select_related("cancelled_by")
    refund_rows = refund_qs.select_related("order", "created_by")
    cashiers = defaultdict(lambda: {"net_sales": ZERO, "refunds": 0, "cancellations": 0})
    for row in pay.values("created_by__username", "kind").annotate(t=Sum("amount"), n=Count("id")):
        c = cashiers[row["created_by__username"]]
        if row["kind"] == "PAYMENT":
            c["net_sales"] += row["t"]
        else:
            c["net_sales"] -= row["t"]; c["refunds"] += row["n"]
    for o in cancelled:
        cashiers[o.cancelled_by.username if o.cancelled_by else "unknown"]["cancellations"] += 1

    subtotal = o_tot["subtotal"] or ZERO
    discount = o_tot["discount"] or ZERO
    return {
        "from": start, "to": end,
        "summary": {
            "gross_sales": gross, "refunds": refunds, "net_sales": net, "orders": n_orders,
            "average_order": (net / n_orders).quantize(CENTS) if n_orders else ZERO,
            "tax": o_tot["tax"] or ZERO, "service_charge": o_tot["service"] or ZERO, "discounts": discount,
            "food_cost": cogs.quantize(CENTS),
            "food_profit": (subtotal - discount - cogs).quantize(CENTS),
        },
        "by_method": by_method,
        "by_day": [{"date": d, "net": v} for d, v in sorted(by_day.items())],
        "by_hour": [{"hour": h, "orders": n} for h, n in by_hour.items()],
        "top_items": items[:15],
        "items_without_recipe": sorted(no_recipe),
        "exceptions": {
            "cancelled": {"count": cancelled.count(), "total": _sum(cancelled, "total_amount"),
                          "orders": [{"order_number": o.order_number, "total": o.total_amount, "reason": o.cancel_reason,
                                      "by": o.cancelled_by.username if o.cancelled_by else None, "at": o.cancelled_at}
                                     for o in cancelled[:30]]},
            "refunds": {"count": refund_rows.count(), "total": refunds,
                        "list": [{"order_number": p.order.order_number, "amount": p.amount, "method": p.method,
                                  "reason": p.reason, "by": p.created_by.username, "at": p.created_at} for p in refund_rows[:30]]},
            "discounts": discount,
        },
        "cashiers": [{"username": u, **v} for u, v in sorted(cashiers.items())],
        "shift_differences": [
            {"id": s.id, "cashier": s.opened_by.username, "closed_at": s.closed_at, "expected": s.expected_cash,
             "counted": s.counted_cash, "difference": s.difference, "location": s.location.name}
            for s in Shift.objects.filter(location__in=locations, status="CLOSED", closed_at__date__gte=start,
                                          closed_at__date__lte=end).exclude(difference=0).select_related("opened_by", "location")
        ],
    }
