from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


class ChangePasswordView(APIView):
    """POST /auth/change-password/ {current_password, new_password}"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        user = request.user
        cur, new = request.data.get("current_password") or "", request.data.get("new_password") or ""
        if not user.check_password(cur):
            raise ValidationError({"current_password": "Your current password is not correct."})
        if cur == new:
            raise ValidationError({"new_password": "Choose a password different from the current one."})
        try:
            validate_password(new, user)
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": list(exc.messages)})
        user.set_password(new)
        user.save(update_fields=["password"])
        return Response({"detail": "Password changed."}, status=status.HTTP_200_OK)
