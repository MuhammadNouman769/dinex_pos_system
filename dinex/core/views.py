from drf_spectacular.utils import (
    OpenApiExample,
    extend_schema,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


@extend_schema(
    summary="Login and obtain JWT tokens",
    description=(
        "Authenticate a user using username and password. "
        "Returns an access token and refresh token."
    ),
    examples=[
        OpenApiExample(
            "Login Example",
            summary="Admin login",
            description="Demo restaurant owner (created by: python manage.py seed_demo).",
            value={
                "username": "karachigrill",
                "password": "Demo@12345",
            },
            request_only=True,
        ),
    ],
)
class LoginAPIView(TokenObtainPairView):
    pass


@extend_schema(
    summary="Refresh access token",
    description=(
        "Generate a new access token using a valid refresh token. "
        "The refresh token must not be expired or blacklisted."
    ),
    examples=[
        OpenApiExample(
            "Refresh Token Example",
            summary="Refresh access token",
            description="Provide the refresh token received during login.",
            value={
                "refresh": "your_refresh_token_here",
            },
            request_only=True,
        ),
    ],
)
class RefreshTokenAPIView(TokenRefreshView):
    pass