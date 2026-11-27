from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

""" ======================= Custom User Admin ======================= """
@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = (
        *UserAdmin.fieldsets,
        (
            "DineX by XverLabs",
            {
                "fields": (
                    "role",
                ),
            },
        ),
    )

    add_fieldsets = (
        *UserAdmin.add_fieldsets,
        (
            "DineX by XverLabs",
            {
                "fields": (
                    "email",
                    "role",
                ),
            },
        ),
    )

    list_display = (
        "username",
        "email",
        "role",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
    )