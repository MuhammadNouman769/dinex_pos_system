"""Loyalty points: earn on paid bills, use as a discount, give back on refunds, email customers."""
import logging
from datetime import timedelta
from decimal import ROUND_FLOOR, Decimal

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.customers.models.customer import Customer
from apps.loyalty.models import LoyaltyEntry, LoyaltySettings

log = logging.getLogger(__name__)
ZERO = Decimal("0")
CENTS = Decimal("0.01")


def get_settings(org_id, create=False):
    if create:
        return LoyaltySettings.objects.get_or_create(organization_id=org_id)[0]
    return LoyaltySettings.objects.filter(organization_id=org_id).first()


def public_rules(org_id):
    """What the app and the printed bill need to know (cached offline inside /auth/me/)."""
    s = get_settings(org_id)
    if not s or not s.enabled:
        return {"enabled": False}
    return {"enabled": True, "spend_per_point": s.spend_per_point, "point_value": s.point_value, "min_redeem": s.min_redeem}


def describe(rules, currency="PKR"):
    """Short, plain-English line for bills and emails."""
    sp, pv = Decimal(str(rules["spend_per_point"])), Decimal(str(rules["point_value"]))
    n = int(rules["min_redeem"])
    fmt = lambda v: f"{v.normalize():f}"
    return (f"Earn 1 point for every {currency} {fmt(sp)} you spend. 1 point = {currency} {fmt(pv)} off your bill. "
            f"You can use your points once you have {n} or more.")


def link_customer(location, name="", phone="", email=""):
    """Find or create the customer record for this phone number (loyalty only)."""
    phone = (phone or "").strip()
    if not phone:
        return None
    c = Customer.objects.filter(location=location, phone=phone).first()
    name, email = (name or "").strip(), (email or "").strip().lower()
    if c is None:
        first, _, last = (name or "Guest").partition(" ")
        c = Customer.objects.create(location=location, phone=phone, first_name=first[:100] or "Guest", last_name=last[:100],
                                    email=email or None, customer_type=Customer.CustomerType.REGULAR)
    else:
        changed = []
        if email and not c.email:
            c.email, changed = email, changed + ["email"]
        if name and c.first_name == "Guest":
            c.first_name, _, c.last_name = name.partition(" ")
            changed += ["first_name", "last_name"]
        if changed:
            c.save(update_fields=changed + ["updated_at"])
    return c


def _entry(customer, kind, points, order=None, value=ZERO, note=""):
    """Move the balance and write the ledger line in one step (balance never goes below zero)."""
    c = Customer.objects.select_for_update().get(pk=customer.pk)
    new = max(0, c.points_balance + points)
    applied = new - c.points_balance
    Customer.objects.filter(pk=c.pk).update(points_balance=new)
    customer.points_balance = new
    return LoyaltyEntry.objects.create(customer=c, order=order, kind=kind, points=applied, balance_after=new, value=value, note=note[:200])


def points_for(settings, amount):
    return int((Decimal(str(amount)) / settings.spend_per_point).to_integral_value(rounding=ROUND_FLOOR))


@transaction.atomic
def earn_for_order(order):
    """Called when a bill becomes fully paid. Safe to call twice."""
    if not order.customer_id:
        return None
    s = get_settings(order.location.organization_id)
    if not s or not s.enabled or s.spend_per_point <= 0:
        return None
    if LoyaltyEntry.objects.filter(order=order, kind="EARN").exists():
        return None
    pts = points_for(s, order.total_amount)
    if pts <= 0:
        return None
    e = _entry(order.customer, "EARN", pts, order=order, note=f"Bill {order.order_number}")
    transaction.on_commit(lambda: email_points(e.customer, order, e, s))
    return e


@transaction.atomic
def redeem(order, points, user):
    if not order.customer_id:
        raise ValidationError({"detail": "Add the customer's phone number to this order first."})
    s = get_settings(order.location.organization_id)
    if not s or not s.enabled:
        raise ValidationError({"detail": "Loyalty points are not switched on."})
    from apps.cash import services as cash
    order = type(order).objects.select_for_update().get(pk=order.pk)
    if LoyaltyEntry.objects.filter(order=order, kind="REDEEM").exists():
        raise ValidationError({"detail": "Points were already used on this bill."})
    if order.payments.exists():
        raise ValidationError({"detail": "Use points before taking payment."})
    customer = Customer.objects.get(pk=order.customer_id)
    try:
        points = int(points)
    except (TypeError, ValueError):
        raise ValidationError({"points": "Enter a whole number."})
    if points <= 0:
        raise ValidationError({"points": "Enter how many points to use."})
    if customer.points_balance < s.min_redeem:
        raise ValidationError({"detail": f"Points can be used from {s.min_redeem} points. This customer has {customer.points_balance}."})
    if points > customer.points_balance:
        raise ValidationError({"points": f"This customer has only {customer.points_balance} points."})
    value = (Decimal(points) * s.point_value).quantize(CENTS)
    if value > order.total_amount:
        raise ValidationError({"points": f"That is more than the bill. At most {int(order.total_amount / s.point_value)} points can be used."})
    order.discount = (order.discount or ZERO) + value
    order.save(update_fields=["discount", "updated_at"])
    order.calculate_totals()
    _entry(customer, "REDEEM", -points, order=order, value=value, note=f"Bill {order.order_number}")
    cash.audit(user, order.location, "points_redeemed", order, points=points, value=value, customer=customer.full_name)
    return order


@transaction.atomic
def reverse_for_order(order):
    """A fully refunded bill: take back what it earned, give back what it used."""
    if not order.customer_id:
        return
    customer = Customer.objects.get(pk=order.customer_id)
    got = LoyaltyEntry.objects.filter(order=order, kind="EARN").first()
    if got and not LoyaltyEntry.objects.filter(order=order, kind="EARN_REVERSED").exists():
        _entry(customer, "EARN_REVERSED", -got.points, order=order, note="Bill refunded")
    used = LoyaltyEntry.objects.filter(order=order, kind="REDEEM").first()
    if used and not LoyaltyEntry.objects.filter(order=order, kind="REDEEM_RETURNED").exists():
        _entry(customer, "REDEEM_RETURNED", -used.points, order=order, note="Bill refunded")


def order_info(order):
    """What the cashier and the bill show for this order, or None."""
    if not order.customer_id:
        return None
    s = get_settings(order.location.organization_id)
    if not s or not s.enabled:
        return None
    earned = LoyaltyEntry.objects.filter(order=order, kind="EARN").first()
    used = LoyaltyEntry.objects.filter(order=order, kind="REDEEM").first()
    c = order.customer
    return {"customer": c.full_name, "balance": c.points_balance, "earned": earned.points if earned else 0,
            "redeemed": -used.points if used else 0, "redeemed_value": used.value if used else 0,
            "can_redeem": c.points_balance >= s.min_redeem and not used and not order.payments.exists(),
            "min_redeem": s.min_redeem, "point_value": s.point_value}


# ───────────── emails ─────────────
def _send(org, to, subject, body):
    from django.conf import settings as dj
    import re
    addr = re.search(r"<(.+)>", dj.DEFAULT_FROM_EMAIL)
    sender = f"{org.name} <{addr.group(1) if addr else dj.DEFAULT_FROM_EMAIL}>"
    send_mail(subject, body, sender, [to], fail_silently=False)


def email_points(customer, order, entry, s):
    if not (s.email_customers and customer.email):
        return
    org = order.location.organization
    rules = {"spend_per_point": s.spend_per_point, "point_value": s.point_value, "min_redeem": s.min_redeem}
    body = (f"Hi {customer.first_name},\n\nThank you for visiting {org.name}.\n\n"
            f"You earned {entry.points} point{'s' if entry.points != 1 else ''} on bill {order.order_number}.\n"
            f"Your points balance is now {entry.balance_after} (worth {org.currency} {(Decimal(entry.balance_after) * s.point_value).normalize():f}).\n\n"
            f"{describe(rules, org.currency)}\n\nSee you again soon!\n{org.name}")
    try:
        _send(org, customer.email, f"You earned {entry.points} points at {org.name}", body)
    except Exception:   # an email problem must never block a sale
        log.exception("loyalty email failed")


def send_reminders(org, now=None, min_gap_days=3):
    """Remind customers with points. At most one email per customer every `min_gap_days` (so 1-2 a week)."""
    now = now or timezone.now()
    s = get_settings(org.id)
    if not s or not s.enabled or not s.reminders:
        return {"sent": 0, "skipped": 0}
    due = Customer.objects.filter(location__organization=org, is_active=True, points_balance__gt=0).exclude(email__isnull=True).exclude(email="")
    sent = skipped = 0
    rules = {"spend_per_point": s.spend_per_point, "point_value": s.point_value, "min_redeem": s.min_redeem}
    for c in due:
        if c.last_reminder_at and now - c.last_reminder_at < timedelta(days=min_gap_days):
            skipped += 1
            continue
        worth = (Decimal(c.points_balance) * s.point_value).normalize()
        ready = c.points_balance >= s.min_redeem
        body = (f"Hi {c.first_name},\n\nYou have {c.points_balance} loyalty points at {org.name}, worth {org.currency} {worth:f}.\n"
                + (f"They are ready to use on your next visit.\n" if ready else f"Collect {s.min_redeem - c.points_balance} more points and you can start using them.\n")
                + f"\n{describe(rules, org.currency)}\n\nWe would love to see you again!\n{org.name}")
        try:
            _send(org, c.email, f"You have {c.points_balance} points at {org.name}", body)
            Customer.objects.filter(pk=c.pk).update(last_reminder_at=now)
            sent += 1
        except Exception:
            log.exception("loyalty reminder failed")
            skipped += 1
    return {"sent": sent, "skipped": skipped}
