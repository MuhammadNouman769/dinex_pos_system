from django.db import models
from apps.utils.models import BaseModel
from apps.orders.models.choices import TableShape, TableStatus

class Table(BaseModel):
    TableStatus = TableStatus

    """
    Table Model - For Dine In
    """
    location = models.ForeignKey(
        "organizations.Location",
        on_delete=models.CASCADE,
        related_name="tables",
        help_text="Location"
    )

    floor = models.ForeignKey(
        "orders.Floor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tables",
        help_text="Floor / area this table is on",
    )

    table_number = models.CharField(
        max_length=20,
        help_text="Table number (e.g., T-1, T-5)"
    )

    capacity = models.PositiveIntegerField(
        default=2,
        help_text="Seating capacity"
    )

    status = models.CharField(
        max_length=20,
        choices=TableStatus.choices,
        default=TableStatus.AVAILABLE,
        db_index=True,
        help_text="Table status"
    )

    shape = models.CharField(
        max_length=10,
        choices=TableShape.choices,
        default=TableShape.SQUARE,
        help_text="How the table is drawn on the floor plan",
    )

    pos_x = models.PositiveIntegerField(null=True, blank=True, help_text="Floor plan position (px), empty = auto")
    pos_y = models.PositiveIntegerField(null=True, blank=True, help_text="Floor plan position (px), empty = auto")

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["table_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "table_number"],
                condition=models.Q(is_deleted=False),
                name="unique_table_per_location",
            ),
        ]

    def __str__(self):
        return f"Table {self.table_number} ({self.location.name})"

    def is_available(self):
        return self.status == Table.TableStatus.AVAILABLE

    def occupy(self):
        self.status = Table.TableStatus.OCCUPIED
        self.save()

    def free(self):
        self.status = Table.TableStatus.AVAILABLE
        self.save()