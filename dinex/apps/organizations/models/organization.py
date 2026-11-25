from django.db import models

from apps.utils.models import BaseModel


""" ======================= Organization Model ======================= """
class Organization(BaseModel):

    name = models.CharField(
        max_length=255,
    )

    currency = models.CharField(
        max_length=3,
        default="PKR",
    )

    timezone = models.CharField(
        max_length=50,
        default="Asia/Karachi",
    )

    is_active = models.BooleanField(
        default=True,
    )

    # ---- Bill branding / payment details (printed on receipts) ----
    logo = models.ImageField(upload_to="org/logos/", null=True, blank=True)
    logo_bw = models.TextField(blank=True, default="", help_text="Black-and-white PNG (data URI) used on thermal bills")
    payment_qr_bw = models.TextField(blank=True, default="", help_text="Payment QR as black-and-white PNG (data URI)")
    payment_qr_text = models.CharField(max_length=255, blank=True, default="", help_text="Text/URL turned into a QR when no QR picture is uploaded")
    payment_accounts = models.JSONField(default=list, blank=True, help_text="[{label, title, number}] printed at the bottom of the bill")
    receipt_footer = models.CharField(max_length=200, blank=True, default="")
    bill_show_logo = models.BooleanField(default=True)
    bill_show_accounts = models.BooleanField(default=True)
    bill_show_qr = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name