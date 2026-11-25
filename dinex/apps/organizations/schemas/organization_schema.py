from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)

from apps.organizations.serializers.organization_serializer import (
    OrganizationDetailSerializer,
)


organization_retrieve_schema = extend_schema(
    tags=["Organizations"],
    summary="Retrieve organization",
    description=(
        "Retrieve a single organization by ID. Accessible by platform "
        "users (any organization) or the organization's own owner."
    ),
    responses={
        200: OpenApiResponse(response=OrganizationDetailSerializer),
        404: OpenApiResponse(description="Organization not found."),
    },
)

organization_update_schema = extend_schema(
    tags=["Organizations"],
    summary="Update organization",
    description="Update organization name, currency or timezone.",
    request=OrganizationDetailSerializer,
    responses={
        200: OpenApiResponse(response=OrganizationDetailSerializer),
        400: OpenApiResponse(description="Validation error."),
    },
)

organization_me_schema = extend_schema(
    tags=["Organizations"],
    summary="Get my organization",
    description="Returns the organization the current user belongs to.",
    responses={
        200: OpenApiResponse(response=OrganizationDetailSerializer),
        403: OpenApiResponse(description="User has no organization assigned."),
    },
)

organization_toggle_active_schema = extend_schema(
    tags=["Organizations"],
    summary="Activate/deactivate organization",
    description="Platform-only. Toggles or sets `is_active` on an organization.",
    request=None,
    responses={200: OpenApiResponse(response=OrganizationDetailSerializer)},
)

organization_list_schema = extend_schema(
    summary="List organizations",
    description=(
        "Returns all organizations available on the platform. "
        "This endpoint can only be accessed by a platform user. "
        "Each organization includes all of its locations."
    ),
    responses={
        200: OpenApiResponse(
            description=(
                "List of organizations with their locations."
            ),
        ),
    },
    examples=[
        OpenApiExample(
            "Organization List",
            value=[
                {
                    "id": 1,
                    "name": "The Makar",
                    "currency": "PKR",
                    "timezone": "Asia/Karachi",
                    "is_active": True,
                    "locations": [
                        {
                            "id": 1,
                            "name": "Lahore",
                            "address": "Gulberg, Lahore",
                            "phone": "03001234567",
                            "is_active": True,
                            "is_primary": True,
                            "created_at": "2026-09-02T10:00:00Z",
                            "updated_at": "2026-09-02T10:00:00Z",
                        },
                        {
                            "id": 2,
                            "name": "Karachi",
                            "address": "DHA, Karachi",
                            "phone": "03001234568",
                            "is_active": True,
                            "is_primary": False,
                            "created_at": "2026-09-02T10:00:00Z",
                            "updated_at": "2026-09-02T10:00:00Z",
                        },
                        {
                            "id": 3,
                            "name": "Islamabad",
                            "address": "F-7, Islamabad",
                            "phone": "03001234569",
                            "is_active": True,
                            "is_primary": False,
                            "created_at": "2026-09-02T10:00:00Z",
                            "updated_at": "2026-09-02T10:00:00Z",
                        },
                    ],
                    "created_at": "2026-09-02T10:00:00Z",
                    "updated_at": "2026-09-02T10:00:00Z",
                }
            ],
            response_only=True,
        ),
    ],
)