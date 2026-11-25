from  rest_framework import serializers
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)
from apps.onboarding.serializers.restaurant_serializer import (
    RestaurantOnboardingSerializer,
)

# ============================================
# RESPONSE SCHEMA
# ============================================

class RestaurantOnboardingResponseSchema(serializers.Serializer):
    """Schema for restaurant onboarding response"""
    message = serializers.CharField(help_text="Success message")
    organization_id = serializers.IntegerField(help_text="Organization ID")
    owner_id = serializers.IntegerField(help_text="Owner user ID")
    location_id = serializers.IntegerField(help_text="Location ID")
    membership_id = serializers.IntegerField(help_text="Membership ID")


# ============================================
# ONBOARDING SCHEMA
# ============================================

restaurant_onboarding_schema = extend_schema(
    tags=["Onboarding"],
    summary="Create restaurant",
    description=(
        "Create a complete restaurant setup in a single "
        "atomic transaction. Only authenticated Platform "
        "users can perform this operation. "
        "The operation creates the Owner user, Organization, "
        "Organization Membership and Location."
    ),
    request=RestaurantOnboardingSerializer,
    examples=[
        OpenApiExample(
            name="Restaurant Setup",
            summary="Create restaurant with owner and location",
            description="Complete first-time restaurant setup.",
            value={
                "organization": {
                    "name": "The Makar",
                    "currency": "PKR",
                    "timezone": "Asia/Karachi",
                },
                "owner": {
                    "username": "Nouman",
                    "email": "nouman@example.com",
                    "password": "SecurePassword@123",
                    "first_name": "muhammad",
                    "last_name": "nouman",
                },
                "location": {
                    "name": "Main Branch",
                    "address": "Islamabad, Pakistan",
                    "phone": "03001234567",
                    "is_primary": True,
                },
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=RestaurantOnboardingResponseSchema,  
            description="Restaurant created successfully."
        ),
        400: OpenApiResponse(
            description="Validation error."
        ),
        401: OpenApiResponse(
            description="Authentication credentials were not provided or token is invalid."
        ),
        403: OpenApiResponse(
            description="Only Platform users can create restaurants."
        ),
    },
)