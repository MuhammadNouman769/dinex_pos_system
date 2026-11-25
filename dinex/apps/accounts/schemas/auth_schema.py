from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import (
    OpenApiExample,
    extend_schema,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
)

""" ======================= Platform Login API View Schema ======================= """
@extend_schema(
    tags=["Authentication"],
    summary="Login and obtain JWT tokens",
    description=(
        "Authenticate a platform or restaurant user "
        "using username and password. "
        "Returns an access token and refresh token."
    ),
    examples=[
        OpenApiExample(
            name="Platform Login",
            summary="Platform user login",
            description=(
                "Login using a platform account "
                "created through Django Admin."
            ),
            value={
                "username": "platform",
                "password": "Platform@12345",
            },
            request_only=True,
        ),
    ],
)
class LoginAPIView(TokenObtainPairView):
    throttle_scope = "login"          # brute-force protection, see LOGIN_RATE
    throttle_classes = [ScopedRateThrottle]