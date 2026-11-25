"""DineX Admin API (XverLabs staff) + the restaurant's own billing view."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Max, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import payments, services
from apps.billing.models import Invoice, PaymentAccount, PaymentSubmission, Plan, Subscription
from apps.cash.models import AuditLog, Payment
from apps.catalog.utils import get_user_organization_id
from apps.onboarding.serializers.restaurant_serializer import RestaurantOnboardingSerializer
from apps.onboarding.services import create_restaurant
from apps.orders.models import Order
from apps.organizations.models import Location, Organization, OrganizationMembership
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.permissions import IsPlatformUser

User = get_user_model()
PLATFORM = [IsAuthenticated, IsPlatformUser]


def _plan_dict(p):
    return {"id": p.id, "code": p.code, "name": p.name, "description": p.description, "price_monthly": p.price_monthly,
            "max_locations": p.max_locations, "max_users": p.max_users, "features": p.features, "is_active": p.is_active,
            "sort_order": p.sort_order, "restaurants": p.subscriptions.count()}


def _invoice_dict(i):
    return {"id": i.id, "number": i.number, "organization": i.organization_id, "organization_name": i.organization.name,
            "period_start": i.period_start, "period_end": i.period_end, "amount": i.amount, "status": i.status,
            "issued_at": i.issued_at, "due_date": i.due_date, "paid_at": i.paid_at, "method": i.method,
            "reference": i.reference, "note": i.note,
            "overdue": i.status == Invoice.Status.DUE and i.due_date < timezone.localdate()}


def _owner_of(org):
    m = OrganizationMembership.objects.filter(organization=org, role=OrganizationMembership.Role.OWNER).select_related("user").order_by("id").first()
    return m.user if m else None


def _org_usage(org):
    since = timezone.now() - timedelta(days=30)
    orders = Order.objects.filter(location__organization=org)
    sales = Payment.objects.filter(shift__location__organization=org, created_at__gte=since)
    net = (sales.filter(kind="PAYMENT").aggregate(t=Sum("amount"))["t"] or Decimal("0")) - (sales.filter(kind="REFUND").aggregate(t=Sum("amount"))["t"] or Decimal("0"))
    return {**services.usage(org), "orders_30d": orders.filter(created_at__gte=since).count(), "sales_30d": net,
            "last_order_at": orders.aggregate(m=Max("created_at"))["m"]}


def _restaurant_row(org):
    owner, sub = _owner_of(org), services.subscription_of(org)
    return {
        "id": org.id, "name": org.name, "currency": org.currency, "is_active": org.is_active, "created_at": org.created_at,
        "owner": {"id": owner.id, "name": owner.get_full_name() or owner.username, "username": owner.username, "email": owner.email} if owner else None,
        "subscription": {"status": sub.status, "plan": sub.plan.code, "plan_name": sub.plan.name, "price": sub.price,
                         "trial_ends_at": sub.trial_ends_at, "current_period_end": sub.current_period_end,
                         "suspended_reason": sub.suspended_reason} if sub else None,
        "usage": _org_usage(org),
        "invoices_due": org.invoices.filter(status="DUE").count(),
    }


# ───────────────────────── overview ─────────────────────────
class PlatformOverviewView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        now, today = timezone.now(), timezone.localdate()
        subs = Subscription.objects.select_related("plan", "organization")
        by_status = {s: 0 for s in Subscription.Status.values}
        mrr = Decimal("0")
        for sub in subs:
            by_status[sub.status] += 1
            if sub.status in (Subscription.Status.ACTIVE, Subscription.Status.PAST_DUE):
                mrr += sub.price
        since = now - timedelta(days=30)
        sales = Payment.objects.filter(created_at__gte=since)
        processed = (sales.filter(kind="PAYMENT").aggregate(t=Sum("amount"))["t"] or Decimal("0")) - (sales.filter(kind="REFUND").aggregate(t=Sum("amount"))["t"] or Decimal("0"))
        overdue = Invoice.objects.filter(status="DUE", due_date__lt=today)
        ending = subs.filter(status="TRIAL", trial_ends_at__gte=now, trial_ends_at__lte=now + timedelta(days=7))
        month_start = today.replace(day=1)
        return Response({
            "restaurants": Organization.objects.count(), "by_status": by_status, "mrr": mrr,
            "new_this_month": Organization.objects.filter(created_at__date__gte=month_start).count(),
            "orders_30d": Order.objects.filter(created_at__gte=since).count(), "sales_processed_30d": processed,
            "collected_this_month": Invoice.objects.filter(status="PAID", paid_at__date__gte=month_start).aggregate(t=Sum("amount"))["t"] or Decimal("0"),
            "pending_payments": PaymentSubmission.objects.filter(status="PENDING").count(),
            "overdue": {"count": overdue.count(), "amount": overdue.aggregate(t=Sum("amount"))["t"] or Decimal("0")},
            "trials_ending": [{"id": s.organization_id, "name": s.organization.name, "ends": s.trial_ends_at} for s in ending[:8]],
            "recent": [_restaurant_row(o) for o in Organization.objects.order_by("-created_at")[:5]],
            "overdue_list": [_invoice_dict(i) for i in overdue.select_related("organization")[:8]],
        })


# ───────────────────────── plans ─────────────────────────
class PlanListCreateView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        return Response([_plan_dict(p) for p in Plan.objects.all()])

    def post(self, request):
        return Response(_save_plan(Plan(), request.data), status=status.HTTP_201_CREATED)


class PlanDetailView(APIView):
    permission_classes = PLATFORM

    def patch(self, request, pk):
        return Response(_save_plan(get_object_or_404(Plan, pk=pk), request.data))


def _save_plan(plan, data):
    errors = {}
    def num(key, cast, minimum=0):
        if key not in data:
            return getattr(plan, key, None)
        try:
            v = cast(str(data[key]))
        except (ValueError, InvalidOperation):
            errors[key] = "Enter a number."; return None
        if v < minimum:
            errors[key] = f"Must be at least {minimum}."
        return v
    new = plan.pk is None
    if new and not data.get("name"):
        errors["name"] = "Required."
    code = (data.get("code") or plan.code or "").strip().lower()
    if new and not code:
        errors["code"] = "Required."
    if new and Plan.objects.filter(code=code).exists():
        errors["code"] = "A plan with this code already exists."
    price = num("price_monthly", Decimal)
    max_locations, max_users = num("max_locations", int, 1), num("max_users", int, 1)
    if new and "price_monthly" not in data:
        errors["price_monthly"] = "Required."
    if errors:
        raise ValidationError(errors)
    if new:
        plan.code = code
    plan.name = data.get("name", plan.name)
    plan.description = data.get("description", plan.description)
    plan.price_monthly = price if price is not None else plan.price_monthly
    plan.max_locations = max_locations or plan.max_locations or 1
    plan.max_users = max_users or plan.max_users or 5
    if "features" in data:
        plan.features = [str(f)[:120] for f in (data["features"] or [])][:12]
    if "is_active" in data:
        plan.is_active = bool(data["is_active"])
    if "sort_order" in data:
        plan.sort_order = int(data["sort_order"])
    plan.save()
    return _plan_dict(plan)


# ───────────────────────── restaurants ─────────────────────────
class RestaurantListCreateView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        qs = Organization.objects.all().order_by("-created_at")
        q = request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(memberships__user__username__icontains=q, memberships__role="OWNER")
                           | Q(memberships__user__email__icontains=q, memberships__role="OWNER")).distinct()
        st = request.query_params.get("status")
        if st in Subscription.Status.values:
            qs = qs.filter(subscription__status=st)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([_restaurant_row(o) for o in page])

    @transaction.atomic
    def post(self, request):
        serializer = RestaurantOnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        plan = Plan.objects.filter(code=request.data.get("plan"), is_active=True).first() if request.data.get("plan") else services.default_plan()
        if plan is None:
            raise ValidationError({"plan": "Unknown plan."})
        try:
            days = int(request.data.get("trial_days", 14))
        except (TypeError, ValueError):
            raise ValidationError({"trial_days": "Enter a number of days."})
        owner, org, location = create_restaurant(d["organization"], d["owner"], d["location"])
        sub = services.start_trial(org, plan, days)
        if request.data.get("activate"):
            services.apply_action(sub, request.user, "activate", {})
        services.platform_audit(request.user, org, "restaurant_created", plan=plan.code, owner=owner.username)
        return Response(_restaurant_row(org), status=status.HTTP_201_CREATED)


class RestaurantDetailView(APIView):
    permission_classes = PLATFORM

    def get(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)
        sub = services.subscription_of(org)
        users = OrganizationMembership.objects.filter(organization=org).select_related("user").order_by("role", "id")
        return Response({
            **_restaurant_row(org),
            "subscription_detail": {"notes": sub.notes, "price_override": sub.price_override, "plan_price": sub.plan.price_monthly,
                                    "current_period_start": sub.current_period_start} if sub else None,
            "locations": [{"id": l.id, "name": l.name, "address": l.address, "is_active": l.is_active} for l in Location.objects.filter(organization=org)],
            "users": [{"id": m.user_id, "username": m.user.username, "name": m.user.get_full_name(), "email": m.user.email,
                       "role": m.role, "is_active": m.is_active, "last_login": m.user.last_login} for m in users],
            "invoices": [_invoice_dict(i) for i in org.invoices.select_related("organization")[:24]],
            "activity": [{"action": a.action, "user": a.user.username if a.user else None, "details": a.details, "created_at": a.created_at}
                         for a in AuditLog.objects.filter(organization=org, action__startswith="platform_").select_related("user")[:15]],
            "status_info": services.status_info(org),
        })

    def patch(self, request, pk):       # enable / disable the whole account
        org = get_object_or_404(Organization, pk=pk)
        if "is_active" in request.data:
            org.is_active = bool(request.data["is_active"])
            org.save(update_fields=["is_active", "updated_at"])
            services.platform_audit(request.user, org, "account_enabled" if org.is_active else "account_disabled")
        return Response(_restaurant_row(org))


class SubscriptionActionView(APIView):
    permission_classes = PLATFORM

    def post(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)
        sub = services.subscription_of(org)
        if sub is None:
            sub = services.start_trial(org)
        services.apply_action(sub, request.user, request.data.get("action"), request.data)
        return Response(_restaurant_row(org))


class ResetOwnerPasswordView(APIView):
    """Support tool: set a new password for the restaurant's owner."""
    permission_classes = PLATFORM

    def post(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)
        owner = _owner_of(org)
        if owner is None:
            raise ValidationError({"detail": "This restaurant has no owner."})
        password = request.data.get("password") or ""
        try:
            validate_password(password, owner)
        except DjangoValidationError as exc:
            raise ValidationError({"password": list(exc.messages)})
        owner.set_password(password)
        owner.save(update_fields=["password"])
        services.platform_audit(request.user, org, "owner_password_reset", owner=owner.username)
        return Response({"detail": f"Password changed for {owner.username}."})


class RestaurantInvoiceCreateView(APIView):
    permission_classes = PLATFORM

    def post(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)
        sub = services.subscription_of(org)
        if sub is None:
            raise ValidationError({"detail": "This restaurant has no subscription."})
        today = timezone.localdate()
        try:
            amount = Decimal(str(request.data["amount"])) if request.data.get("amount") not in (None, "") else None
        except InvalidOperation:
            raise ValidationError({"amount": "Enter a valid amount."})
        start = sub.current_period_end or today
        inv = services.create_invoice(sub, start, services.add_months(start), amount=amount, note=request.data.get("note", ""))
        services.platform_audit(request.user, org, "invoice_created", invoice=inv.number, amount=inv.amount)
        return Response(_invoice_dict(inv), status=status.HTTP_201_CREATED)


# ───────────────────────── invoices ─────────────────────────
class InvoiceListView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        qs = Invoice.objects.select_related("organization")
        st = request.query_params.get("status")
        if st == "OVERDUE":
            qs = qs.filter(status="DUE", due_date__lt=timezone.localdate())
        elif st in Invoice.Status.values:
            qs = qs.filter(status=st)
        q = request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(organization__name__icontains=q))
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([_invoice_dict(i) for i in page])


class InvoicePayView(APIView):
    permission_classes = PLATFORM

    def post(self, request, pk):
        inv = services.mark_paid(get_object_or_404(Invoice, pk=pk), request.user, request.data.get("method", ""), request.data.get("reference", ""))
        return Response(_invoice_dict(inv))


class InvoiceVoidView(APIView):
    permission_classes = PLATFORM

    def post(self, request, pk):
        return Response(_invoice_dict(services.void_invoice(get_object_or_404(Invoice, pk=pk), request.user)))


# ───────────────────────── the restaurant's own view ─────────────────────────
def _owner_org(request):
    org_id = get_user_organization_id(request)
    if not org_id:
        raise PermissionDenied("User has no organization assigned.")
    org = Organization.objects.get(pk=org_id)
    if not OrganizationMembership.objects.filter(user=request.user, organization=org, role="OWNER", is_active=True).exists():
        raise PermissionDenied("Only the owner can see billing.")
    return org


class MyBillingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _owner_org(request)
        return Response({
            "subscription": services.status_info(org), "usage": services.usage(org),
            "invoices": [_invoice_dict(i) for i in org.invoices.select_related("organization")[:24]],
            "plans": [_plan_dict(p) for p in Plan.objects.filter(is_active=True)],
            "payment_accounts": [payments.account_dict(a) for a in PaymentAccount.objects.filter(is_active=True)],
            "submissions": [payments.submission_dict(x, request) for x in org.payment_submissions.select_related("invoice")[:20]],
        })


class MyPaymentsView(APIView):
    """The owner tells DineX 'I paid': transaction id, amount, optional screenshot."""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        org = _owner_org(request)
        sub = payments.submit_payment(org, request.user, request.data, request.FILES.get("proof"))
        return Response(payments.submission_dict(sub, request), status=status.HTTP_201_CREATED)


class MySelectPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        org = _owner_org(request)
        payments.choose_plan(org, request.user, request.data.get("plan"))
        return Response({"subscription": services.status_info(org)})


# ───────────────────────── payment queue + accounts (XverLabs) ─────────────────────────
class PaymentSubmissionListView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        qs = PaymentSubmission.objects.select_related("organization", "invoice", "submitted_by")
        st = request.query_params.get("status")
        if st in PaymentSubmission.Status.values:
            qs = qs.filter(status=st)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([payments.submission_dict(x, request, with_org=True) for x in page])


class PaymentSubmissionApproveView(APIView):
    permission_classes = PLATFORM

    def post(self, request, pk):
        sub = payments.approve_submission(get_object_or_404(PaymentSubmission, pk=pk), request.user)
        return Response(payments.submission_dict(sub, request, with_org=True))


class PaymentSubmissionRejectView(APIView):
    permission_classes = PLATFORM

    def post(self, request, pk):
        sub = payments.reject_submission(get_object_or_404(PaymentSubmission, pk=pk), request.user, request.data.get("reason"))
        return Response(payments.submission_dict(sub, request, with_org=True))


def _save_account(acct, data):
    errors = {}
    method = data.get("method", acct.method)
    if method not in PaymentAccount.Method.values:
        errors["method"] = "Choose JazzCash, Easypaisa, Bank or Other."
    title = str(data.get("account_title", acct.account_title) or "").strip()
    number = str(data.get("account_number", acct.account_number) or "").strip()
    if not title:
        errors["account_title"] = "Required."
    if not number:
        errors["account_number"] = "Required."
    if errors:
        raise ValidationError(errors)
    acct.method, acct.account_title, acct.account_number = method, title[:120], number[:60]
    acct.bank_name = str(data.get("bank_name", acct.bank_name) or "")[:80]
    acct.instructions = str(data.get("instructions", acct.instructions) or "")[:255]
    if "is_active" in data:
        acct.is_active = bool(data["is_active"])
    if "sort_order" in data:
        acct.sort_order = int(data["sort_order"] or 0)
    acct.save()
    return payments.account_dict(acct)


class PaymentAccountListCreateView(APIView):
    permission_classes = PLATFORM

    def get(self, request):
        return Response([payments.account_dict(a) for a in PaymentAccount.objects.all()])

    def post(self, request):
        return Response(_save_account(PaymentAccount(), request.data), status=status.HTTP_201_CREATED)


class PaymentAccountDetailView(APIView):
    permission_classes = PLATFORM

    def patch(self, request, pk):
        return Response(_save_account(get_object_or_404(PaymentAccount, pk=pk), request.data))

    def delete(self, request, pk):
        get_object_or_404(PaymentAccount, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
