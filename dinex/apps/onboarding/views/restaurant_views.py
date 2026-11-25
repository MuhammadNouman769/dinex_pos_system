from django.db import transaction
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    Location,
)
from apps.onboarding.schemas.restaurant_schema import (
    restaurant_onboarding_schema,
)
from apps.onboarding.serializers.restaurant_serializer import (
    RestaurantOnboardingSerializer,
)
User = get_user_model()

""" ======================= Restaurant Onboarding API View ======================= """
@restaurant_onboarding_schema
class RestaurantOnboardingAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):

        # ============================================================
        # PLATFORM USER CHECK
        # ============================================================

        if request.user.role != User.Role.PLATFORM:
            return Response(
                {
                    "detail": (
                        "Only a platform user can "
                        "create a organization."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ============================================================
        # VALIDATE REQUEST
        # ============================================================

        serializer = RestaurantOnboardingSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        data = serializer.validated_data

        organization_data = data["organization"]
        owner_data = data["owner"]
        location_data = data["location"]

        # ============================================================
        # TRANSACTION
        # ============================================================

        from apps.onboarding.services import create_restaurant
        from apps.billing import services as billing

        with transaction.atomic():
            owner, organization, location = create_restaurant(organization_data, owner_data, location_data)
            billing.start_trial(organization)      # every new restaurant starts on a free trial
            membership = organization.memberships.get(user=owner)

        # ============================================================
        # RESPONSE
        # ============================================================

        return Response(
            {
                "message": (
                    "Restaurant created successfully."
                ),
                "organization": {
                    "id": organization.id,
                    "name": organization.name,
                    "currency": organization.currency,
                    "timezone": organization.timezone,
                },
                "owner": {
                    "id": owner.id,
                    "username": owner.username,
                    "email": owner.email,
                    "first_name": owner.first_name,
                    "last_name": owner.last_name,
                    "role": owner.role,
                },
                "membership": {
                    "id": membership.id,
                    "role": membership.role,
                },
                "location": {
                    "id": location.id,
                    "name": location.name,
                    "address": location.address,
                    "phone": location.phone,
                    "is_primary": location.is_primary,
                },
            },
            status=status.HTTP_201_CREATED,
        )