from django.conf import settings
from django.db import models

from apps.utils.models import BaseModel

""" ======================= Organization Membership Model ======================= """
class OrganizationMembership(BaseModel):

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        STAFF = "STAFF", "Staff"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
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
                    "user",
                    "organization",
                ],
                name="unique_user_organization_membership",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.organization} - "
            f"{self.role}"
        )