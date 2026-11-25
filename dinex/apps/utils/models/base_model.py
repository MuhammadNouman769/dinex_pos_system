import uuid

from django.db import models
from django.utils import timezone
from django.utils.text import slugify

""" ======================= Base Model ======================= """
class SoftDeleteQuerySet(models.QuerySet):
    """
    QuerySet providing soft-delete functionality.
    """
    def delete(self):
        return self.update(
            is_deleted=True,
            updated_at=timezone.now(),
        )

    def hard_delete(self):
        return super().delete()

    def restore(self):
        return self.update(
            is_deleted=False,
            updated_at=timezone.now(),
        )

    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

""" ======================= Soft Delete Manager ======================= """
class SoftDeleteManager(
    models.Manager.from_queryset(SoftDeleteQuerySet)
):
    """
    Default manager that excludes soft-deleted records.
    """

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_deleted=False)
        )

""" ======================= Base Model ======================= """
class BaseModel(models.Model):
    """
    Base model for application business models.
    """

    id = models.BigAutoField(
        primary_key=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
    )

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def delete(
        self,
        using=None,
        keep_parents=False,
    ):
        self.is_deleted = True

        self.save(
            update_fields=[
                "is_deleted",
                "updated_at",
            ],
        )

    def hard_delete(
        self,
        using=None,
        keep_parents=False,
    ):
        return super().delete(
            using=using,
            keep_parents=keep_parents,
        )

    def restore(self):
        self.is_deleted = False

        self.save(
            update_fields=[
                "is_deleted",
                "updated_at",
            ],
        )

    @property
    def is_active(self):
        return not self.is_deleted

""" ======================= UUID Base Model ======================= """
class UUIDBaseModel(BaseModel):
    """
    Base model using UUID as primary key.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        abstract = True

""" ======================= Ordered Model ======================= """
class OrderedModel(BaseModel):
    """
    Base model for objects that require ordering.
    """

    position = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        abstract = True
        ordering = [
            "position",
            "-created_at",
        ]

    def save(self, *args, **kwargs):
        if self.position is None and self._state.adding:
            max_position = (
                self.__class__
                .objects
                .aggregate(
                    max_position=models.Max("position")
                )
                ["max_position"]
            )

            self.position = (
                max_position or 0
            ) + 1

        super().save(*args, **kwargs)

""" ======================= Slugged Model ======================= """
class SluggedModel(BaseModel):
    """
    Base model for models requiring a unique slug.
    """

    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
    )

    SLUG_FIELD = "name"

    class Meta:
        abstract = True

    def generate_slug(self):
        value = getattr(
            self,
            self.SLUG_FIELD,
            "",
        )

        if not value:
            raise ValueError(
                f"{self.SLUG_FIELD} must have a value."
            )

        base_slug = slugify(value)
        slug = base_slug
        counter = 1

        queryset = (
            self.__class__
            .all_objects
            .exclude(pk=self.pk)
        )

        while queryset.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_slug()

        super().save(*args, **kwargs)