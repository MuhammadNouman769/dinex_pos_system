from django.conf import settings
from django.db import models


class EmailCode(models.Model):
    """A short-lived 6-digit code sent by email (password reset, or confirming a new email address)."""
    class Purpose(models.TextChoices):
        RESET = "RESET", "Password reset"
        VERIFY = "VERIFY", "Confirm email"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_codes")
    purpose = models.CharField(max_length=8, choices=Purpose.choices)
    email = models.EmailField(help_text="Where the code was sent")
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "purpose", "-created_at"])]
