from django.db import models
from apps.utils.models import BaseModel


class Floor(BaseModel):
    """
    A floor / area of a location: Basement, Ground Floor, First Floor, Rooftop...
    Added by the restaurant owner during setup; tables are placed on floors.
    """
    location = models.ForeignKey(
        "organizations.Location",
        on_delete=models.CASCADE,
        related_name="floors",
    )
    name = models.CharField(max_length=100, help_text="e.g. Ground Floor")
    level = models.IntegerField(
        default=0,
        help_text="Sort order by height: -1 basement, 0 ground, 1 first floor...",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_floor_name_per_location",
            ),
        ]

    def __str__(self):
        return f"{self.location.name} - {self.name}"
