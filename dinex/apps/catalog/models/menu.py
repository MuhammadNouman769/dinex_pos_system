from django.db import models

from apps.organizations.models import Organization, Location
from apps.utils.models import BaseModel


class Menu(BaseModel):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="menus",
    )

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="unique_menu_slug_per_organization",
            ),
        ]

    def __str__(self):
        return self.name


class MenuSchedule(BaseModel):

    class WeekDay(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name="schedules",
    )

    day_of_week = models.PositiveSmallIntegerField(
        choices=WeekDay.choices,
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["day_of_week", "start_time"]


class MenuSection(BaseModel):

    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name="sections",
    )

    name = models.CharField(
        max_length=255,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["display_order", "name"]


class MenuItem(BaseModel):

    section = models.ForeignKey(
        MenuSection,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="menu_items",
    )

    display_name = models.CharField(
        max_length=255,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    price_override = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    is_available = models.BooleanField(
        default=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["display_order", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "section",
                    "product_variant",
                ],
                name="unique_variant_per_menu_section",
            ),
        ]

    def __str__(self):
        return self.display_name or self.product_variant.name


class LocationProduct(BaseModel):

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="product_configurations",
    )

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="location_configurations",
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    price_override = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "location",
                    "product",
                ],
                name="unique_location_product",
            ),
        ]


class LocationMenu(BaseModel):

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="menu_assignments",
    )

    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name="location_assignments",
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["location", "menu"],
                name="unique_location_menu",
            ),
        ]


class LocationMenuItem(BaseModel):

    location_menu = models.ForeignKey(
        LocationMenu,
        on_delete=models.CASCADE,
        related_name="items",
    )

    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="location_assignments",
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    price_override = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "location_menu",
                    "menu_item",
                ],
                name="unique_location_menu_item",
            ),
        ]