from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.organizations.models import (
    Organization,
    Location,
)


User = get_user_model()

""" ======================= Restaurant Onboarding Serializer ======================= """
class OrganizationOnboardingSerializer(
    serializers.Serializer
):
    name = serializers.CharField(
        max_length=255,
    )
    currency = serializers.CharField(
        max_length=3,
        default="PKR",
    )
    timezone = serializers.CharField(
        max_length=50,
        default="Asia/Karachi",
    )
    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Organization name cannot be empty."
            )
        return value

""" ======================= Owner Onboarding Serializer ======================= """
class OwnerOnboardingSerializer(
    serializers.Serializer
):
    username = serializers.CharField(
        max_length=150,
    )
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    first_name = serializers.CharField(
        max_length=150,
    )

    last_name = serializers.CharField(
        max_length=150,
    )

    def validate_username(self, value):
        value = value.strip()

        if User.objects.filter(
            username__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "This username is already registered."
            )

        return value

    def validate_email(self, value):
        value = value.lower().strip()

        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "This email is already registered."
            )

        return value

""" ======================= Location Onboarding Serializer ======================= """
class LocationOnboardingSerializer(
    serializers.Serializer
):
    name = serializers.CharField(
        max_length=255,
    )
    address = serializers.CharField()

    phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
    )
    is_primary = serializers.BooleanField(
        default=True,
    )
    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Location name cannot be empty."
            )
        return value

    def validate_address(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Address cannot be empty."
            )

        return value

""" ======================= Restaurant Onboarding Serializer ======================= """
class RestaurantOnboardingSerializer(
    serializers.Serializer
):

    organization = OrganizationOnboardingSerializer()

    owner = OwnerOnboardingSerializer()

    location = LocationOnboardingSerializer()

    def validate(self, attrs):

        organization_data = attrs["organization"]
        location_data = attrs["location"]

        if (
            Organization.objects.filter(
                name__iexact=organization_data["name"]
            ).exists()
        ):
            raise serializers.ValidationError({
                "organization": {
                    "name": (
                        "An organization with this "
                        "name already exists."
                    )
                }
            })

        return attrs