import re

from rest_framework import serializers

from apps.utils.serializers import OrganizationScopedMixin
from apps.staff.models import Employee, Role


class EmployeeSerializer(OrganizationScopedMixin, serializers.ModelSerializer):
    org_scoped_fields = {"location": "organization_id"}
    location_scoped_fields = {"location": "id"}

    location_name = serializers.CharField(source="location.name", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True, default=None)
    has_pin = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ["id", "code", "name", "role", "role_display", "location", "location_name", "phone", "cnic", "address",
                  "emergency_contact", "joining_date", "is_active", "vehicle", "delivery_commission",
                  "username", "has_pin", "created_at"]
        read_only_fields = ["id", "code", "created_at"]

    def get_has_pin(self, obj):
        return bool(obj.pin_hash)

    def validate_name(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Enter the employee's name.")
        return value

    def validate_phone(self, value):
        value = value.strip()
        if value and not re.fullmatch(r"\+?[0-9][0-9\- ]{6,18}", value):
            raise serializers.ValidationError("Enter a valid phone number.")
        return value

    def validate_cnic(self, value):
        digits = re.sub(r"[\s-]", "", value or "")
        if digits and not re.fullmatch(r"\d{13}", digits):
            raise serializers.ValidationError("CNIC must have 13 digits.")
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}" if digits else ""

    def validate(self, data):
        role = data.get("role") or (self.instance.role if self.instance else Role.WAITER)
        commission = data.get("delivery_commission")
        if commission is not None and commission > 0 and role != Role.RIDER:
            raise serializers.ValidationError({"delivery_commission": "Only riders get a delivery commission."})
        if self.instance and "role" in data and data["role"] != self.instance.role and self.instance.role == Role.RIDER:
            from apps.staff import services
            if services.unsettled_orders(self.instance):
                raise serializers.ValidationError({"role": "This rider still owes cash. Settle it before changing the role."})
        return data
