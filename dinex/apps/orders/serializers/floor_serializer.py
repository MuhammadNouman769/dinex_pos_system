from rest_framework import serializers
from apps.utils.serializers import OrganizationScopedMixin
from apps.orders.models import Floor


class FloorSerializer(OrganizationScopedMixin, serializers.ModelSerializer):
    org_scoped_fields = {"location": "organization_id"}
    location_scoped_fields = {"location": "id"}

    table_count = serializers.SerializerMethodField()

    class Meta:
        model = Floor
        fields = ["id", "location", "name", "level", "is_active", "table_count",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_table_count(self, obj):
        return obj.tables.filter(is_deleted=False).count()

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Floor name is required.")
        return value

    def validate(self, data):
        location = data.get("location") or (self.instance.location if self.instance else None)
        name = data.get("name") or (self.instance.name if self.instance else None)
        if location and name:
            qs = Floor.objects.filter(location=location, name__iexact=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"name": f"'{name}' already exists at this location."})
        return data
