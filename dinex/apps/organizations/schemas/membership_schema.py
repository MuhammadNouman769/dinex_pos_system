from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)

from apps.organizations.serializers.membership_serializer import (
    MembershipSerializer,
    MembershipInviteSerializer,
    MembershipUpdateSerializer,
)


membership_list_schema = extend_schema(
    tags=["Organization Members"],
    summary="List organization members",
    responses={200: OpenApiResponse(response=MembershipSerializer(many=True))},
)

membership_invite_schema = extend_schema(
    tags=["Organization Members"],
    summary="Add a member to the organization",
    description=(
        "Attach an existing user via `user_id`, or create a brand new "
        "user in the same call by providing username/email/password/"
        "first_name/last_name. Exactly one of the two must be used."
    ),
    request=MembershipInviteSerializer,
    examples=[
        OpenApiExample(
            "Attach existing user",
            value={"user_id": 5, "role": "STAFF"},
            request_only=True,
        ),
        OpenApiExample(
            "Create and invite a new user",
            value={
                "username": "manager_ali",
                "email": "ali@example.com",
                "password": "secure-password",
                "first_name": "Ali",
                "last_name": "Raza",
                "role": "STAFF",
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(response=MembershipSerializer),
        400: OpenApiResponse(description="Validation error."),
    },
)

membership_retrieve_schema = extend_schema(
    tags=["Organization Members"],
    summary="Retrieve a member",
    responses={200: OpenApiResponse(response=MembershipSerializer)},
)

membership_update_schema = extend_schema(
    tags=["Organization Members"],
    summary="Update a member's role or active status",
    description="Rejected if this would leave the organization with no active OWNER.",
    request=MembershipUpdateSerializer,
    responses={
        200: OpenApiResponse(response=MembershipSerializer),
        400: OpenApiResponse(description="Would leave the organization without an active owner."),
    },
)

membership_delete_schema = extend_schema(
    tags=["Organization Members"],
    summary="Remove a member from the organization",
    description="Rejected if this is the organization's last active OWNER.",
    responses={
        204: OpenApiResponse(description="Member removed."),
        400: OpenApiResponse(description="Cannot remove the last active owner."),
    },
)
