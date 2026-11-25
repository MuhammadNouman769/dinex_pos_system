from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from apps.cash import services as cash
from apps.cash.models import CashMovement, Shift
from apps.inventory import services as inv
from apps.operations.models import Expense, Purchase, PurchaseLine, Reservation

ZERO = Decimal("0")
CENTS = Decimal("0.01")


def q2(v):
    return Decimal(str(v)).quantize(CENTS)


# ───────────── reservations ─────────────
ACTIVE = (Reservation.Status.BOOKED, Reservation.Status.SEATED)


def check_reservation(location, table, party_size, starts_at, duration, exclude_id=None):
    if table is not None:
        if table.location_id != location.id:
            raise ValidationError({"table": "That table belongs to another branch."})
        if party_size > table.capacity:
            raise ValidationError({"party_size": f"Table {table.table_number} seats only {table.capacity}."})
        end = starts_at + timedelta(minutes=duration)
        near = Reservation.objects.filter(table=table, status__in=ACTIVE,
                                          starts_at__gte=starts_at - timedelta(days=1), starts_at__lte=end)
        if exclude_id:
            near = near.exclude(pk=exclude_id)
        for r in near:
            if r.starts_at < end and r.starts_at + timedelta(minutes=r.duration_minutes) > starts_at:
                raise ValidationError({"table": f"Table {table.table_number} is already booked "
                                                f"by {r.guest_name} at that time."})


# ───────────── purchases ─────────────
@transaction.atomic
def receive_purchase(location, supplier, date, lines, paid, invoice_no, note, user):
    """lines: [{ingredient, quantity, unit, unit_cost}] -> stocks every line in and records the bill."""
    if not lines:
        raise ValidationError({"lines": "Add at least one item."})
    built, total = [], ZERO
    for ln in lines:
        ing = ln["ingredient"]
        try:
            factor = inv.unit_factor(ln.get("unit"), ing)
        except ValueError as exc:
            raise ValidationError({"lines": f"{ing.name}: {exc}"})
        qty, cost = Decimal(str(ln["quantity"])), Decimal(str(ln["unit_cost"]))
        line_total = q2(qty * cost)
        built.append((ing, qty, ln.get("unit", ""), cost, factor, line_total))
        total += line_total
    paid = q2(paid or 0)
    if paid < 0 or paid > total:
        raise ValidationError({"paid": "Paid must be between 0 and the bill total."})
    p = Purchase.objects.create(location=location, supplier=supplier, invoice_no=invoice_no[:50], date=date,
                                total=total, paid=paid, note=note[:255], created_by=user)
    for ing, qty, unit, cost, factor, line_total in built:
        PurchaseLine.objects.create(purchase=p, ingredient=ing, quantity=qty, unit=unit, unit_cost=cost, line_total=line_total)
        inv.purchase(location, ing, qty * factor, cost / factor, user=user,
                     note=f"Purchase #{p.id}" + (f" · {supplier.name}" if supplier else ""))
    cash.audit(user, location, "purchase_received", p, total=total, supplier=supplier.name if supplier else "")
    return p


# ───────────── expenses ─────────────
@transaction.atomic
def add_expense(location, user, date, category, amount, description, source):
    amount = q2(amount)
    if amount <= 0:
        raise ValidationError({"amount": "Amount must be greater than zero."})
    if not category.strip():
        raise ValidationError({"category": "Choose a category."})
    movement = None
    if source == Expense.Source.DRAWER:
        shift = cash.current_shift(user, location.id)
        if shift is None:
            raise ValidationError({"source": "Open your shift first to pay from the cash drawer."})
        try:
            movement = cash.add_movement(shift, user, "EXPENSE", amount, reason=description or category, category=category)
        except cash.CashError as exc:
            raise ValidationError({"detail": str(exc)})
    return Expense.objects.create(location=location, date=date, category=category.strip()[:50], description=description[:255],
                                  amount=amount, source=source, movement=movement, created_by=user)


# ───────────── end-of-day (Z) report ─────────────
def day_report(locations, day):
    sales = cash.sales_report(locations, day, day)
    exp = Expense.objects.filter(location__in=locations, date=day)
    by_cat = defaultdict(lambda: ZERO)
    for e in exp:
        by_cat[e.category] += e.amount
    # drawer expenses entered from the Cash desk (not through Expenses) still count
    loose = CashMovement.objects.filter(shift__location__in=locations, kind="EXPENSE", created_at__date=day, expense__isnull=True)
    for m in loose:
        by_cat[m.category or "Other"] += m.amount
    expenses_total = sum(by_cat.values(), ZERO)

    pur = Purchase.objects.filter(location__in=locations, date=day)
    pt = pur.aggregate(total=Sum("total"), paid=Sum("paid"))
    purchases_total, purchases_paid = pt["total"] or ZERO, pt["paid"] or ZERO

    shifts = Shift.objects.filter(location__in=locations).filter(opened_at__date=day) | \
        Shift.objects.filter(location__in=locations, closed_at__date=day)
    shift_rows, drawer = [], {"cash_in": ZERO, "cash_out": ZERO, "safe_drops": ZERO}
    for s in shifts.distinct().select_related("opened_by", "location").order_by("opened_at"):
        sm = cash.shift_summary(s)
        for k in drawer:
            drawer[k] += sm[k]
        shift_rows.append({"id": s.id, "cashier": sm["cashier"], "location": s.location.name, "opened_at": s.opened_at,
                           "closed_at": s.closed_at, "still_open": s.status == "OPEN", "opening_cash": s.opening_cash,
                           "expected_cash": sm["expected_cash"], "counted_cash": s.counted_cash, "difference": s.difference})
    res = Reservation.objects.filter(location__in=locations, starts_at__date=day)
    net = sales["summary"]["net_sales"]
    return {
        "date": day, "locations": [l.name for l in locations],
        "sales": sales["summary"], "by_method": sales["by_method"], "exceptions": sales["exceptions"],
        "top_items": sales["top_items"][:8],
        "expenses": {"total": expenses_total, "by_category": [{"category": k, "amount": v} for k, v in sorted(by_cat.items(), key=lambda x: -x[1])]},
        "purchases": {"count": pur.count(), "total": purchases_total, "paid": purchases_paid, "unpaid": purchases_total - purchases_paid},
        "drawer": drawer, "shifts": shift_rows,
        "open_shifts": sum(1 for s in shift_rows if s["still_open"]),
        "cash_short_over": sum((s["difference"] or ZERO for s in shift_rows), ZERO),
        "reservations": {"total": res.count(), "seated": res.filter(status="SEATED").count() + res.filter(status="COMPLETED").count(),
                         "no_show": res.filter(status="NO_SHOW").count(), "cancelled": res.filter(status="CANCELLED").count()},
        "net_after_costs": net - expenses_total - purchases_paid,
    }
