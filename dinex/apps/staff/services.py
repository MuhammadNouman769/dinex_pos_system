"""Staff logic: employee codes, rider ledger and cash settlement."""
import re
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, F, Sum
from django.utils import timezone

from apps.cash import services as cash
from apps.staff.models import Employee, RiderSettlement

ZERO = Decimal("0.00")


def next_code(organization):
    nums = [int(m.group(1)) for c in Employee.all_objects.filter(organization=organization).values_list("code", flat=True)
            if (m := re.fullmatch(r"E-(\d+)", c))]
    return f"E-{(max(nums) + 1) if nums else 1:03d}"


# ───────────────────────── riders ─────────────────────────
def unsettled_orders(rider):
    """Delivered orders whose money is still with the rider (cash on delivery, not yet handed in)."""
    from apps.orders.models import Order
    rows = (Order.objects.filter(rider=rider, order_type="DELIVERY", status="COMPLETED")
            .select_related("location").order_by("created_at"))
    return [(o, cash.amount_due(o)) for o in rows if cash.amount_due(o) > 0]


def rider_summary(rider):
    from apps.orders.models import Order
    today = timezone.localdate()
    mine = Order.objects.filter(rider=rider, order_type="DELIVERY")
    on_road = mine.filter(status="OUT_FOR_DELIVERY")
    pending = unsettled_orders(rider)
    done_today = mine.filter(status="COMPLETED", delivered_at__date=today)
    month = mine.filter(status="COMPLETED", delivered_at__gte=timezone.now() - timedelta(days=30))
    avg = month.exclude(dispatched_at=None).aggregate(a=Avg(F("delivered_at") - F("dispatched_at")))["a"]
    return {
        "on_road": on_road.count(),
        "on_road_value": on_road.aggregate(t=Sum("total_amount"))["t"] or ZERO,
        "to_settle_orders": len(pending),
        "to_settle": sum((d for _, d in pending), ZERO),
        "delivered_today": done_today.count(),
        "delivered_30d": month.count(),
        "avg_delivery_minutes": round(avg.total_seconds() / 60, 1) if avg else None,
    }


@transaction.atomic
def settle(rider, user, handed, order_ids=None, note=""):
    """
    The rider hands cash to the cashier. The cash is recorded as CASH payments on the rider's orders
    (oldest first) inside the cashier's open shift. If less than expected is handed over, the missing
    amount stays due on the orders and is recorded as the settlement's shortage.
    """
    shift = cash.current_shift(user, rider.location_id)
    if shift is None:
        raise cash.CashError("Open your shift before taking cash from a rider.")
    pending = unsettled_orders(rider)
    if order_ids is not None:
        wanted = {int(i) for i in order_ids}
        if not wanted:
            raise cash.CashError("Select at least one order.")
        pending = [(o, d) for o, d in pending if o.id in wanted]
        if len(pending) != len(wanted):
            raise cash.CashError("Some selected orders are not waiting for settlement from this rider.")
    if not pending:
        raise cash.CashError("This rider has no cash to settle.")
    expected = sum((d for _, d in pending), ZERO)
    handed = cash.q2(handed)
    if handed < 0:
        raise cash.CashError("Cash handed over cannot be negative.")
    if handed > expected:
        raise cash.CashError(f"The rider owes {expected}; you cannot receive more than that.")

    s = RiderSettlement.objects.create(
        rider=rider, location=rider.location, shift=shift, received_by=user, expected=expected, handed=handed,
        shortage=expected - handed, order_ids=[o.id for o, _ in pending], note=(note or "")[:255])
    remaining = handed
    for order, due in pending:
        pay = min(due, remaining)
        if pay > 0:
            cash.take_payment(order, user, "CASH", pay, reference=f"RS-{s.id}")
            remaining -= pay
    if s.shortage > 0:
        cash.audit(user, rider.location, "rider_shortage", rider, rider=rider.name, expected=expected,
                   handed=handed, shortage=s.shortage)
    return s


def employee_stats(emp):
    """Small numbers shown on an employee's page."""
    from apps.orders.models import Order
    since = timezone.now() - timedelta(days=30)
    if emp.role == "RIDER":
        return {"kind": "rider", **rider_summary(emp)}
    served = Order.objects.filter(waiter=emp, created_at__gte=since).exclude(status="CANCELLED")
    agg = served.aggregate(n=Count("id"), sales=Sum("total_amount"))
    n = agg["n"] or 0
    return {"kind": "waiter", "orders_30d": n, "sales_30d": agg["sales"] or ZERO,
            "average_bill": (agg["sales"] / n).quantize(Decimal("0.01")) if n else ZERO}
