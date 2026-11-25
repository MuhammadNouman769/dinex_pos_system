from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


""" ======================= New-Or-Existing User Fields ======================= """
class UserResolutionSerializer(serializers.Serializer):
    """
    Base serializer for endpoints that either attach an existing user
    (`user_id`) or create a brand new one (username/email/password/
    first_name/last_name) — never both.
    """

    # NOTE: only users who already have (or had) a membership in the caller's
    # organization can be referenced by id. Otherwise any restaurant could
    # attach - and read the details of - users of other restaurants.
    user_id = serializers.IntegerField(required=False)

    username = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)

    NEW_USER_FIELDS = {"username", "email", "password", "first_name", "last_name"}

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate_user_id(self, value):
        from apps.organizations.models import OrganizationMembership

        organization = self.context["organization"]
        # all_objects: also match removed (soft-deleted) members so they can be re-added
        member = OrganizationMembership.all_objects.filter(
            user_id=value, organization=organization
        ).select_related("user").first()
        if member is None:
            raise serializers.ValidationError(
                "No such user in your organization. To add a new person, "
                "send username, email, password, first_name and last_name."
            )
        return member.user

    def validate(self, attrs):
        provided_new_user_fields = self.NEW_USER_FIELDS & attrs.keys()

        if attrs.get("user_id") and provided_new_user_fields:
            raise serializers.ValidationError(
                "Provide either `user_id` or new-user details, not both."
            )

        if not attrs.get("user_id") and provided_new_user_fields != self.NEW_USER_FIELDS:
            raise serializers.ValidationError(
                "Provide `user_id`, or all of: "
                "username, email, password, first_name, last_name."
            )

        if not attrs.get("user_id"):
            if User.objects.filter(username__iexact=attrs["username"]).exists():
                raise serializers.ValidationError(
                    {"username": "This username is already registered."}
                )
            if User.objects.filter(email__iexact=attrs["email"]).exists():
                raise serializers.ValidationError(
                    {"email": "This email is already registered."}
                )

        return attrs

    def resolve_user(self, validated_data):
        """
        Returns the target user, creating one if new-user fields were given.
        Must be called inside a transaction by the caller.
        """
        user = validated_data.get("user_id")
        if user:
            return user

        user = User(
            username=validated_data["username"],
            email=validated_data["email"].lower().strip(),
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role=User.Role.OWNER,
            is_active=True,
        )
        user.set_password(validated_data["password"])
        user.save()
        return user
