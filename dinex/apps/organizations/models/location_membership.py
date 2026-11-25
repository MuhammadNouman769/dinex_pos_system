from django.db import models
from apps.utils.models import BaseModel

""" ======================= Location Membership Model ======================= """
class LocationMembership(BaseModel):
    class Role(models.TextChoices):
        MANAGER = "MANAGER", "Manager"
        POS_OPERATOR = (
            "POS_OPERATOR",
            "POS Operator",
        )

    organization_membership = models.ForeignKey(
        "organizations.OrganizationMembership",
        on_delete=models.CASCADE,
        related_name="location_memberships",
    )

    location = models.ForeignKey(
        "organizations.Location",
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
    )

    is_active = models.BooleanField(
        default=True,
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization_membership",
                    "location",
                ],
                name="unique_organization_membership_location",
            ),
        ]

    def __str__(self):
        return (
            f"{self.organization_membership.user} - "
            f"{self.location} - "
            f"{self.role}"
        )