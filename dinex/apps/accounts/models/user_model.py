from django.contrib.auth.models import AbstractUser
from django.db import models

from django.contrib.auth.models import UserManager


class PlatformAwareUserManager(UserManager):
    """`manage.py createsuperuser` creates a PLATFORM (XverLabs staff) user."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "PLATFORM")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        PLATFORM = "PLATFORM", "Platform"
        OWNER = "OWNER", "Owner"
    
    objects = PlatformAwareUserManager()

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.OWNER,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_full_name() or self.username