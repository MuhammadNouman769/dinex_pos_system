"""API documentation helpers (drf-spectacular): keeps /api/docs/ free of warnings."""
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes


class SubscriptionJWTScheme(OpenApiAuthenticationExtension):
    """Documents our subscription-aware JWT login as a normal Bearer token."""
    target_class = "apps.billing.auth.SubscriptionAwareJWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT",
                "description": "Paste the `access` token from POST /api/v1/auth/token/."}


class DineXAutoSchema(AutoSchema):
    """Plain APIViews have no serializer: describe them as a JSON object instead of warning."""

    def _has_serializer(self):
        return hasattr(self.view, "get_serializer") or hasattr(self.view, "serializer_class")

    def get_response_serializers(self):
        return super().get_response_serializers() if self._has_serializer() else OpenApiTypes.OBJECT

    def get_request_serializer(self):
        if self._has_serializer():
            return super().get_request_serializer()
        return OpenApiTypes.OBJECT if self.method in ("POST", "PUT", "PATCH") else None

    def get_operation_id(self):
        op = super().get_operation_id()
        # list and detail GETs of one plain view would otherwise both be "..._retrieve"
        if self.method == "GET" and not self.path.rstrip("/").endswith("}") and op.endswith("_retrieve"):
            return op[: -len("retrieve")] + "list"
        if "{action}" in self.path and not op.endswith("_action"):
            return op + "_action"
        return op
