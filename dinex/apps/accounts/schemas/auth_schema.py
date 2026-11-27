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
            name="XverLabs admin",
            summary="DineX Admin (platform) login",
            description="Demo admin created by: python manage.py seed_demo",
            value={"username": "xverlabs", "password": "DineX@2026"},
            request_only=True,
        ),
        OpenApiExample(
            name="Restaurant owner",
            summary="Demo restaurant owner login",
            description="Karachi Grill owner created by: python manage.py seed_demo",
            value={"username": "karachigrill", "password": "Demo@12345"},
            request_only=True,
        ),
    ],
)
class LoginAPIView(TokenObtainPairView):
    throttle_scope = "login"          # brute-force protection, see LOGIN_RATE
    throttle_classes = [ScopedRateThrottle]