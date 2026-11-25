from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)

from apps.organizations.serializers.location_serializer import (
    LocationSerializer,
)


LOCATION_EXAMPLE = {
    "id": 2,
    "organization": 1,
    "name": "Karachi Branch",
    "address": "DHA, Karachi",
    "phone": "03001234568",
    "is_active": True,
    "is_primary": False,
    "created_at": "2026-09-02T10:00:00Z",
    "updated_at": "2026-09-02T10:00:00Z",
}


location_list_schema = extend_schema(
    tags=["Locations"],
    summary="List locations",
    description="List all locations belonging to the caller's organization.",
    responses={200: OpenApiResponse(response=LocationSerializer(many=True))},
)

location_create_schema = extend_schema(
    tags=["Locations"],
    summary="Create location",
    description=(
        "Create a new location under the caller's organization. "
        "Setting `is_primary=true` automatically unsets any other "
        "primary location for the organization."
    ),
    request=LocationSerializer,
    examples=[
        OpenApiExample(
            "Create Location",
            value={
                "name": "Karachi Branch",
                "address": "DHA, Karachi",
                "phone": "03001234568",
                "is_primary": False,
            },
            request_only=True,
        ),
    ],
    responses={201: OpenApiResponse(response=LocationSerializer, examples=[
        OpenApiExample("Location Created", value=LOCATION_EXAMPLE, response_only=True),
    ])},
)

location_retrieve_schema = extend_schema(
    tags=["Locations"],
    summary="Retrieve location",
    responses={
        200: OpenApiResponse(response=LocationSerializer, examples=[
            OpenApiExample("Location", value=LOCATION_EXAMPLE, response_only=True),
        ]),
        404: OpenApiResponse(description="Location not found."),
    },
)

location_update_schema = extend_schema(
    tags=["Locations"],
    summary="Update location",
    description="Full or partial update of a location.",
    request=LocationSerializer,
    responses={
        200: OpenApiResponse(response=LocationSerializer),
        400: OpenApiResponse(description="Validation error."),
        404: OpenApiResponse(description="Location not found."),
    },
)

location_delete_schema = extend_schema(
    tags=["Locations"],
    summary="Delete location",
    description=(
        "Soft delete a location. Rejected if this is the organization's "
        "only remaining active location, or if it is the primary "
        "location and no other active location can take over — set "
        "another location as primary first."
    ),
    responses={
        204: OpenApiResponse(description="Location deleted successfully."),
        400: OpenApiResponse(description="Cannot delete the only/primary location."),
        404: OpenApiResponse(description="Location not found."),
    },
)

location_set_primary_schema = extend_schema(
    tags=["Locations"],
    summary="Set primary location",
    description="Marks this location as primary and unsets any other primary location for the organization.",
    request=None,
    responses={200: OpenApiResponse(response=LocationSerializer)},
)
