"""Public (no login) endpoints: the plans shown on the first screen and self-service signup with a free trial."""
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing import services
from apps.billing.models import Plan
from apps.onboarding.services import create_restaurant

User = get_user_model()
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.@+-]{3,150}$")


def public_plan(p):
    return {"code": p.code, "name": p.name, "description": p.description, "price_monthly": p.price_monthly,
            "max_locations": p.max_locations, "max_users": p.max_users, "features": p.features}


class PublicPlansView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        return Response({"plans": [public_plan(p) for p in Plan.objects.filter(is_active=True)],
                         "trial_days": settings.BILLING_TRIAL_DAYS, "terms_version": settings.TERMS_VERSION, "currency": "PKR"})


class SignupView(APIView):
    """Create a restaurant, its owner login and a free trial on the chosen plan. Returns tokens (signed in)."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "signup"

    def post(self, request):
        d = request.data
        errors = {}

        def text(key, label, min_len=1, max_len=255):
            v = str(d.get(key) or "").strip()
            if len(v) < min_len:
                errors[key] = f"{label} is required." if min_len == 1 else f"{label} is too short."
            return v[:max_len]

        if d.get("accept_terms") is not True:
            errors["accept_terms"] = "You must agree to the Terms of Use to continue."
        plan = Plan.objects.filter(code=d.get("plan"), is_active=True).first()
        if plan is None:
            errors["plan"] = "Choose a plan."
        restaurant = text("restaurant_name", "Restaurant name")
        owner_name = text("owner_name", "Your name")
        address = text("address", "Address", 5, 500)
        phone = text("phone", "Mobile number", 7, 30)
        branch = str(d.get("branch_name") or "").strip()[:255] or "Main branch"
        email = str(d.get("email") or "").strip().lower()
        username = str(d.get("username") or "").strip()
        password = str(d.get("password") or "")

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            errors["email"] = "Enter a valid email address."
        elif User.objects.filter(email__iexact=email).exists():
            errors["email"] = "This email is already registered. Sign in instead."
        if not USERNAME_RE.match(username):
            errors["username"] = "Use 3 or more letters, numbers or . _ - (no spaces)."
        elif User.objects.filter(username__iexact=username).exists():
            errors["username"] = "This username is taken. Try another."
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            errors["password"] = " ".join(exc.messages)
        if errors:
            raise ValidationError(errors)

        first, _, last = owner_name.partition(" ")
        ip = ScopedRateThrottle().get_ident(request) or None
        with transaction.atomic():
            owner, org, _loc = create_restaurant(
                {"name": restaurant, "currency": "PKR", "timezone": "Asia/Karachi"},
                {"username": username, "email": email, "password": password, "first_name": first[:150], "last_name": last.strip()[:150]},
                {"name": branch, "address": address, "phone": phone, "is_primary": True})
            sub = services.start_trial(org, plan)
            sub.terms_version, sub.terms_accepted_at, sub.signup_ip = settings.TERMS_VERSION, timezone.now(), ip
            sub.save(update_fields=["terms_version", "terms_accepted_at", "signup_ip"])
            services.platform_audit(owner, org, "self_signup", plan=plan.code, terms=settings.TERMS_VERSION, ip=ip)
        refresh = RefreshToken.for_user(owner)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh),
                         "subscription": services.status_info(org)}, status=status.HTTP_201_CREATED)
