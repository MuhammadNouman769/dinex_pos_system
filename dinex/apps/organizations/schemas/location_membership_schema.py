from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from drf_spectacular.types import OpenApiTypes

from apps.organizations.serializers.location_membership_serializer import (
    LocationMembershipSerializer,
    LocationMembershipAssignSerializer,
    LocationMembershipUpdateSerializer,
)


location_membership_list_schema = extend_schema(
    tags=["Location Staff"],
    summary="List location staff",
    description="List staff assignments across the organization's locations.",
    parameters=[
        OpenApiParameter(
            name="location_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter by a specific location.",
            required=False,
        ),
    ],
    responses={200: OpenApiResponse(response=LocationMembershipSerializer(many=True))},
)

location_membership_assign_schema = extend_schema(
    tags=["Location Staff"],
    summary="Assign a user to a location",
    description=(
        "Attach an existing user via `user_id`, or create a brand new "
        "user in the same call. If the user isn't yet an organization "
        "member, a STAFF-level OrganizationMembership is created "
        "automatically. Re-assigning a previously removed user "
        "reactivates their existing assignment."
    ),
    request=LocationMembershipAssignSerializer,
    examples=[
        OpenApiExample(
            "Assign existing user",
            value={"location_id": 2, "user_id": 5, "role": "POS_OPERATOR"},
            request_only=True,
        ),
        OpenApiExample(
            "Create and assign a new user",
            value={
                "location_id": 2,
                "username": "cashier_hina",
                "email": "hina@example.com",
                "password": "secure-password",
                "first_name": "Hina",
                "last_name": "Tariq",
                "role": "POS_OPERATOR",
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(response=LocationMembershipSerializer),
        400: OpenApiResponse(description="Validation error."),
    },
)

location_membership_retrieve_schema = extend_schema(
    tags=["Location Staff"],
    summary="Retrieve a location staff assignment",
    responses={200: OpenApiResponse(response=LocationMembershipSerializer)},
)

location_membership_update_schema = extend_schema(
    tags=["Location Staff"],
    summary="Update a location staff assignment's role or active status",
    request=LocationMembershipUpdateSerializer,
    responses={200: OpenApiResponse(response=LocationMembershipSerializer)},
)

location_membership_delete_schema = extend_schema(
    tags=["Location Staff"],
    summary="Remove a location staff assignment",
    responses={204: OpenApiResponse(description="Assignment removed.")},
)
