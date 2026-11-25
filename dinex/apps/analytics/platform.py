"""XverLabs-side analytics: revenue, growth, churn, collections and how healthy each restaurant is."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Max, Q, Sum
from django.utils import timezone

from apps.billing.models import Invoice, Subscription
from apps.cash.models import Payment, Shift
from apps.inventory.models import Recipe, StockMovement
from apps.orders.models import Order
from apps.organizations.models import Organization, OrganizationMembership
from apps.payroll.models import PayrollRun
from apps.staff.models import AttendanceRecord

ZERO = Decimal("0.00")
S = Subscription.Status
FEATURES = [("recipes", "Recipes & food cost"), ("inventory", "Stock tracking"), ("cash_shifts", "Cash shifts"), ("attendance", "Attendance"),
            ("payroll", "Payroll"), ("delivery", "Delivery riders")]


def month_start(d):
    return d.replace(day=1)


def add_month(d, n):
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def last_months(today, n=12):
    first = add_month(month_start(today), -(n - 1))
    return [add_month(first, i) for i in range(n)]


def restaurant_health(org, sub, now):
    """Numbers + a 0-100 score + plain-language reasons for one restaurant."""
    today = timezone.localtime(now).date()
    orders = Order.objects.filter(location__organization=org).exclude(status="CANCELLED")
    o7 = orders.filter(created_at__gte=now - timedelta(days=7)).count()
    p7 = orders.filter(created_at__gte=now - timedelta(days=14), created_at__lt=now - timedelta(days=7)).count()
    last = orders.aggregate(m=Max("created_at"))["m"]
    days_since = (now - last).days if last else None
    pays = Payment.objects.filter(shift__location__organization=org, created_at__gte=now - timedelta(days=30))
    sales = (pays.filter(kind="PAYMENT").aggregate(t=Sum("amount"))["t"] or ZERO) - (pays.filter(kind="REFUND").aggregate(t=Sum("amount"))["t"] or ZERO)
    owner = OrganizationMembership.objects.filter(organization=org, role="OWNER").select_related("user").order_by("id").first()
    login = owner.user.last_login if owner else None
    used = {
        "recipes": Recipe.objects.filter(Q(product_variant__product__organization=org) | Q(ingredient__organization=org), is_deleted=False).exists(),
        "inventory": StockMovement.objects.filter(location__organization=org, created_at__gte=now - timedelta(days=30)).exists(),
        "cash_shifts": Shift.objects.filter(location__organization=org, opened_at__gte=now - timedelta(days=30)).exists(),
        "attendance": AttendanceRecord.objects.filter(employee__organization=org, date__gte=today - timedelta(days=30)).exists(),
        "payroll": PayrollRun.objects.filter(location__organization=org).exists(),
        "delivery": orders.filter(order_type="DELIVERY", rider__isnull=False, created_at__gte=now - timedelta(days=30)).exists(),
    }
    trend = None if p7 == 0 else round((o7 - p7) / p7 * 100, 1)
    recency = 0 if days_since is None else 40 if days_since <= 1 else 30 if days_since <= 3 else 20 if days_since <= 7 else 10 if days_since <= 14 else 0
    momentum = 15 if trend is None else 30 if trend >= 0 else 20 if trend >= -20 else 10 if trend >= -50 else 0
    adoption = round(sum(used.values()) / len(used) * 30)
    score = recency + momentum + adoption
    reasons = []
    if days_since is None:
        reasons.append("Has never taken an order")
    elif days_since > 3:
        reasons.append(f"No orders for {days_since} days")
    if trend is not None and trend <= -30:
        reasons.append(f"Orders down {abs(trend):.0f}% on last week")
    missing = [label for key, label in FEATURES if not used[key]]
    if len(missing) >= 4:
        reasons.append("Uses few features: " + ", ".join(missing[:3]) + "…")
    state = "HEALTHY" if score >= 70 else "WATCH" if score >= 40 else "AT_RISK"
    return {"id": org.id, "name": org.name, "status": sub.status, "plan": sub.plan.name, "price": sub.price, "orders_7d": o7, "orders_prev_7d": p7, "trend": trend,
            "days_since_order": days_since, "sales_30d": sales, "owner_last_login": login, "features": used, "score": score, "health": state, "reasons": reasons}


def platform(now=None):
    now = now or timezone.now()
    today = timezone.localtime(now).date()
    subs = list(Subscription.objects.select_related("plan", "organization"))
    paying = [s for s in subs if s.status in (S.ACTIVE, S.PAST_DUE)]
    mrr = sum((s.price for s in paying), ZERO)

    months = last_months(today)
    billed, collected = defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
    for inv in Invoice.objects.exclude(status=Invoice.Status.VOID):
        billed[month_start(inv.period_start)] += inv.amount
        if inv.status == Invoice.Status.PAID and inv.paid_at:
            collected[month_start(timezone.localtime(inv.paid_at).date())] += inv.amount
    signups = defaultdict(int)
    for c in Organization.objects.values_list("created_at", flat=True):
        signups[month_start(timezone.localtime(c).date())] += 1
    before = sum(n for m, n in signups.items() if m < months[0])
    revenue, growth, running = [], [], before
    for m in months:
        revenue.append({"month": m, "billed": billed[m], "collected": collected[m]})
        running += signups[m]
        growth.append({"month": m, "new": signups[m], "total": running})

    converted = {s.organization_id for s in subs if s.status in (S.ACTIVE, S.PAST_DUE)} | set(Invoice.objects.filter(status=Invoice.Status.PAID).values_list("organization_id", flat=True))
    churned = [s for s in subs if s.status in (S.CANCELLED, S.SUSPENDED)]
    by_status = {k: 0 for k in S.values}
    for s in subs:
        by_status[s.status] += 1
    plans = defaultdict(lambda: {"restaurants": 0, "mrr": ZERO})
    for s in paying:
        plans[s.plan.name]["restaurants"] += 1
        plans[s.plan.name]["mrr"] += s.price

    buckets = {"1-7 days": [0, ZERO], "8-30 days": [0, ZERO], "31+ days": [0, ZERO]}
    for inv in Invoice.objects.filter(status=Invoice.Status.DUE, due_date__lt=today):
        late = (today - inv.due_date).days
        b = buckets["1-7 days" if late <= 7 else "8-30 days" if late <= 30 else "31+ days"]
        b[0] += 1; b[1] += inv.amount

    health = [restaurant_health(s.organization, s, now) for s in subs if s.status in (S.ACTIVE, S.PAST_DUE, S.TRIAL)]
    live = len(health)
    adoption = [{"key": k, "label": label, "restaurants": sum(1 for h in health if h["features"][k]),
                 "pct": round(sum(1 for h in health if h["features"][k]) / live * 100) if live else 0} for k, label in FEATURES]
    health.sort(key=lambda h: h["score"])
    return {
        "mrr": mrr, "arr": mrr * 12, "paying": len(paying), "arpu": (mrr / len(paying)).quantize(Decimal("0.01")) if paying else ZERO,
        "restaurants": len(subs), "by_status": by_status,
        "revenue_by_month": revenue, "growth": growth,
        "funnel": {"started": len(subs), "converted": len(converted), "conversion_pct": round(len(converted) / len(subs) * 100, 1) if subs else None,
                   "churned": len(churned), "churn_pct": round(len(churned) / (len(churned) + len(paying)) * 100, 1) if (churned or paying) else None},
        "by_plan": [{"plan": k, **v, "share": round(float(v["mrr"] / mrr * 100), 1) if mrr else 0} for k, v in sorted(plans.items(), key=lambda kv: -kv[1]["mrr"])],
        "aging": [{"bucket": k, "invoices": v[0], "amount": v[1]} for k, v in buckets.items()],
        "health": health, "at_risk": [h for h in health if h["health"] == "AT_RISK"], "adoption": adoption,
        "top_by_sales": sorted(health, key=lambda h: -h["sales_30d"])[:5], "sales_30d": sum((h["sales_30d"] for h in health), ZERO),
    }
