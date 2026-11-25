"""
Subscription logic for DineX (platform side).

- New restaurants start a free TRIAL. The admin converts them to ACTIVE (first invoice is issued).
- `run_billing` (daily cron) issues the next invoice at the end of each period, marks unpaid
  invoices PAST_DUE after the due date and SUSPENDS after a grace period.
- A SUSPENDED / CANCELLED / expired-trial restaurant becomes READ-ONLY (it can still log in and
  look at its data, but cannot change anything) until the admin reactivates it.
- Restaurants without any subscription row (created before billing existed) are never blocked.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.billing.models import Invoice, Plan, Subscription
from apps.cash.models import AuditLog

S = Subscription.Status


class BillingError(APIException):
    status_code = 400
    default_code = "billing_error"


class SubscriptionBlocked(APIException):
    status_code = 402
    default_code = "subscription_blocked"


class PlanLimitReached(APIException):
    status_code = 402
    default_code = "plan_limit_reached"


def add_months(d: date, n: int = 1) -> date:
    month = d.month - 1 + n
    year, month = d.year + month // 12, month % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def platform_audit(user, organization, action, **details):
    clean = {k: (str(v) if isinstance(v, (Decimal, date)) else v) for k, v in details.items()}
    return AuditLog.objects.create(organization=organization, user=user if getattr(user, "is_authenticated", False) else None,
                                   action=f"platform_{action}", object_type="Subscription", details=clean)


# ───────────────────────── trial / status ─────────────────────────
def default_plan() -> Plan:
    plan = Plan.objects.filter(is_active=True).order_by("sort_order", "price_monthly").first()
    if plan is None:
        raise BillingError("No active plan exists. Create a plan first.")
    return plan


def start_trial(organization, plan=None, days=None):
    plan = plan or default_plan()
    days = settings.BILLING_TRIAL_DAYS if days is None else days
    return Subscription.objects.create(
        organization=organization, plan=plan, status=S.TRIAL, trial_ends_at=timezone.now() + timedelta(days=days))


def block_reason(sub):
    """Why this restaurant is read-only, or None if it can work normally."""
    if sub is None:
        return None
    if sub.status == S.SUSPENDED:
        return sub.suspended_reason or "Your DineX subscription is suspended."
    if sub.status == S.CANCELLED:
        return "Your DineX subscription was cancelled."
    if sub.status == S.TRIAL and sub.trial_ends_at and sub.trial_ends_at < timezone.now():
        return "Your free trial has ended."
    return None


def subscription_of(organization):
    try:
        return organization.subscription
    except Subscription.DoesNotExist:
        return None


def status_info(organization):
    """Small summary for the restaurant's own UI (banner) and the admin lists."""
    sub = subscription_of(organization)
    if sub is None:
        return None
    reason = block_reason(sub)
    due = organization.invoices.filter(status=Invoice.Status.DUE)
    now = timezone.now()
    days_left = None
    if sub.status == S.TRIAL and sub.trial_ends_at:
        days_left = max(0, (sub.trial_ends_at - now).days + (1 if (sub.trial_ends_at - now).days >= 0 else 0))
    amount_due = sum((i.amount for i in due), Decimal("0"))
    if reason:
        message = reason + " Open Billing, pay and send the transaction ID to continue."
    elif sub.status == S.PAST_DUE:
        message = "Your payment is overdue. Please pay to avoid suspension."
    elif days_left is not None and days_left <= 5:
        message = f"Your free trial ends in {days_left} day{'s' if days_left != 1 else ''}."
    else:
        message = ""
    return {
        "status": sub.status, "plan": {"code": sub.plan.code, "name": sub.plan.name, "max_locations": sub.plan.max_locations, "max_users": sub.plan.max_users},
        "price": sub.price, "trial_ends_at": sub.trial_ends_at, "days_left": days_left,
        "current_period_end": sub.current_period_end, "blocked": reason is not None, "message": message,
        "invoices_due": due.count(), "amount_due": amount_due,
    }


# ───────────────────────── limits ─────────────────────────
def usage(organization):
    from apps.organizations.models import Location, OrganizationMembership
    return {
        "locations": Location.objects.filter(organization=organization).count(),
        "users": OrganizationMembership.objects.filter(organization=organization, is_active=True).count(),
    }


def check_limit(organization, kind):
    """Raise before adding a 'locations' or 'users' beyond what the plan allows."""
    sub = subscription_of(organization)
    if sub is None:
        return
    used = usage(organization)[kind]
    limit = sub.plan.max_locations if kind == "locations" else sub.plan.max_users
    if used >= limit:
        label = "branches" if kind == "locations" else "staff accounts"
        raise PlanLimitReached(f"Your {sub.plan.name} plan allows {limit} {label}. Ask XverLabs to upgrade your plan.")


# ───────────────────────── invoices ─────────────────────────
def next_invoice_number(year=None):
    year = year or timezone.localdate().year
    prefix = f"DX-{year}-"
    last = Invoice.objects.filter(number__startswith=prefix).order_by("-number").values_list("number", flat=True).first()
    seq = int(last.rsplit("-", 1)[-1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"


@transaction.atomic
def create_invoice(sub, period_start, period_end, amount=None, due_date=None, note=""):
    amount = Decimal(str(amount)) if amount is not None else sub.price
    if amount <= 0:
        raise BillingError("Invoice amount must be greater than zero.")
    return Invoice.objects.create(
        organization=sub.organization, subscription=sub, number=next_invoice_number(),
        period_start=period_start, period_end=period_end, amount=amount,
        due_date=due_date or (timezone.localdate() + timedelta(days=settings.BILLING_INVOICE_DUE_DAYS)), note=note[:255])


@transaction.atomic
def mark_paid(invoice, user, method="", reference=""):
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status != Invoice.Status.DUE:
        raise BillingError(f"This invoice is already {invoice.get_status_display().lower()}.")
    invoice.status = Invoice.Status.PAID
    invoice.paid_at = timezone.now()
    invoice.method, invoice.reference = method[:30], reference[:100]
    invoice.save()
    sub = invoice.subscription
    if sub is not None:
        if sub.current_period_end is None or invoice.period_end > sub.current_period_end:
            sub.current_period_start, sub.current_period_end = invoice.period_start, invoice.period_end
        still_overdue = sub.organization.invoices.filter(status=Invoice.Status.DUE, due_date__lt=timezone.localdate()).exists()
        if sub.status in (S.TRIAL, S.PAST_DUE, S.SUSPENDED) and not still_overdue:
            sub.status, sub.suspended_reason = S.ACTIVE, ""
        sub.save()
        platform_audit(user, sub.organization, "invoice_paid", invoice=invoice.number, amount=invoice.amount, method=method)
    return invoice


@transaction.atomic
def void_invoice(invoice, user):
    if invoice.status != Invoice.Status.DUE:
        raise BillingError("Only a due invoice can be voided.")
    invoice.status = Invoice.Status.VOID
    invoice.save(update_fields=["status"])
    platform_audit(user, invoice.organization, "invoice_voided", invoice=invoice.number)
    return invoice


# ───────────────────────── admin actions on a subscription ─────────────────────────
@transaction.atomic
def apply_action(sub, user, action, data):
    org = sub.organization
    today = timezone.localdate()

    if action == "change_plan":
        plan = Plan.objects.filter(code=data.get("plan"), is_active=True).first()
        if plan is None:
            raise BillingError("Unknown or inactive plan.")
        used = usage(org)
        if used["locations"] > plan.max_locations or used["users"] > plan.max_users:
            raise BillingError(f"{org.name} uses {used['locations']} branch(es) and {used['users']} user(s): too many for {plan.name}.")
        platform_audit(user, org, "plan_changed", old=sub.plan.code, new=plan.code)
        sub.plan = plan

    elif action == "extend_trial":
        try:
            days = int(data.get("days"))
        except (TypeError, ValueError):
            raise BillingError("Enter the number of days.")
        if not 1 <= days <= 90:
            raise BillingError("Choose between 1 and 90 days.")
        base = max(sub.trial_ends_at or timezone.now(), timezone.now())
        sub.trial_ends_at = base + timedelta(days=days)
        if sub.status in (S.SUSPENDED, S.CANCELLED) or sub.status == S.TRIAL:
            sub.status, sub.suspended_reason = S.TRIAL, ""
        platform_audit(user, org, "trial_extended", days=days)

    elif action == "activate":                      # trial -> paying customer, first invoice issued
        if sub.status == S.ACTIVE:
            raise BillingError("Already active.")
        sub.status, sub.suspended_reason = S.ACTIVE, ""
        sub.current_period_start, sub.current_period_end = today, add_months(today)
        sub.save()
        create_invoice(sub, today, add_months(today), note="First month")
        platform_audit(user, org, "activated", plan=sub.plan.code)
        return sub

    elif action == "suspend":
        reason = (data.get("reason") or "").strip()
        if len(reason) < 3:
            raise BillingError("Give a reason for suspending.")
        sub.status, sub.suspended_reason = S.SUSPENDED, reason[:255]
        platform_audit(user, org, "suspended", reason=reason)

    elif action == "reactivate":
        if sub.status not in (S.SUSPENDED, S.CANCELLED, S.PAST_DUE):
            raise BillingError("Only suspended, cancelled or overdue restaurants can be reactivated.")
        was_paid = sub.current_period_end is not None
        sub.status, sub.suspended_reason = (S.ACTIVE if was_paid else S.TRIAL), ""
        if not was_paid and (sub.trial_ends_at is None or sub.trial_ends_at < timezone.now()):
            sub.trial_ends_at = timezone.now() + timedelta(days=3)
        platform_audit(user, org, "reactivated")

    elif action == "cancel":
        sub.status = S.CANCELLED
        platform_audit(user, org, "cancelled", reason=data.get("reason", ""))

    elif action == "set_price":
        price = data.get("price")
        if price in (None, ""):
            sub.price_override = None
        else:
            try:
                value = Decimal(str(price))
            except Exception:
                raise BillingError("Enter a valid price.")
            if value < 0:
                raise BillingError("Price cannot be negative.")
            sub.price_override = value
        platform_audit(user, org, "price_set", price=sub.price_override)

    elif action == "note":
        sub.notes = (data.get("notes") or "")[:2000]

    else:
        raise BillingError("Unknown action.")
    sub.save()
    return sub


# ───────────────────────── daily job ─────────────────────────
@transaction.atomic
def run_billing(today=None):
    """Issue next invoices, mark overdue, suspend after grace. Safe to run many times a day."""
    today = today or timezone.localdate()
    result = {"invoiced": 0, "past_due": 0, "suspended": 0}

    for sub in Subscription.objects.filter(status__in=[S.ACTIVE, S.PAST_DUE], current_period_end__isnull=False,
                                           current_period_end__lte=today).select_related("organization", "plan"):
        start = sub.current_period_end
        if not Invoice.objects.filter(subscription=sub, period_start=start).exclude(status=Invoice.Status.VOID).exists() and sub.price > 0:
            create_invoice(sub, start, add_months(start), due_date=today + timedelta(days=settings.BILLING_INVOICE_DUE_DAYS))
            result["invoiced"] += 1

    for sub in Subscription.objects.filter(status__in=[S.ACTIVE, S.PAST_DUE]).select_related("organization"):
        oldest = sub.organization.invoices.filter(status=Invoice.Status.DUE, due_date__lt=today).order_by("due_date").first()
        if oldest is None:
            continue
        if (today - oldest.due_date).days > settings.BILLING_GRACE_DAYS:
            sub.status, sub.suspended_reason = S.SUSPENDED, f"Invoice {oldest.number} is unpaid."
            sub.save()
            platform_audit(None, sub.organization, "auto_suspended", invoice=oldest.number)
            result["suspended"] += 1
        elif sub.status == S.ACTIVE:
            sub.status = S.PAST_DUE
            sub.save()
            result["past_due"] += 1
    return result
