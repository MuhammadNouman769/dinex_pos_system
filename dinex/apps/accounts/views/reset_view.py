import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts import email_codes

log = logging.getLogger(__name__)
User = get_user_model()
GENERIC = "If we found an account with an email address, we sent a 6-digit code to it. It works for 10 minutes."
BAD_CODE = "That code is not right or has expired. Ask for a new one."


def _find(identifier):
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    users = list(User.objects.filter(is_active=True).filter(Q(username__iexact=identifier) | Q(email__iexact=identifier))[:2])
    return users[0] if len(users) == 1 else None


class ForgotPasswordView(APIView):
    """Never says whether the account exists."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        user = _find(request.data.get("identifier"))
        if user and user.email:
            try:
                email_codes.issue(user, "RESET", user.email, "Your DineX password reset code", "Use this code to choose a new password:")
            except Exception:
                log.exception("password reset email failed")
        return Response({"detail": GENERIC})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        user = _find(request.data.get("identifier"))
        new = request.data.get("new_password") or ""
        if not user or not email_codes.check(user, "RESET", request.data.get("code")):
            raise ValidationError({"code": BAD_CODE})
        try:
            validate_password(new, user)
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": list(exc.messages)})
        user.set_password(new)
        user.save(update_fields=["password"])
        return Response({"detail": "Password changed. You can sign in now."})


class EmailRequestView(APIView):
    """Add or change my email: we send a code to the NEW address to prove it is yours."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if not request.user.check_password(request.data.get("current_password") or ""):
            raise ValidationError({"current_password": "Your current password is not correct."})
        from django.core.validators import validate_email
        try:
            validate_email(email)
        except DjangoValidationError:
            raise ValidationError({"email": "Enter a valid email address."})
        if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
            raise ValidationError({"email": "This email is already used by another account."})
        try:
            sent = email_codes.issue(request.user, "VERIFY", email, "Confirm your email for DineX", "Use this code to confirm your email address:")
        except Exception:
            log.exception("verify email failed")
            raise ValidationError({"email": "We could not send the email. Check the address and try again."})
        if not sent:
            raise ValidationError({"email": "A code was just sent. Please wait a minute before asking again."})
        return Response({"detail": f"We sent a 6-digit code to {email}."})


class EmailConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        row = email_codes.check(request.user, "VERIFY", request.data.get("code"))
        if not row:
            raise ValidationError({"code": BAD_CODE})
        if User.objects.filter(email__iexact=row.email).exclude(pk=request.user.pk).exists():
            raise ValidationError({"email": "This email is already used by another account."})
        request.user.email = row.email
        request.user.save(update_fields=["email"])
        return Response({"detail": "Email confirmed.", "email": row.email}, status=status.HTTP_200_OK)
