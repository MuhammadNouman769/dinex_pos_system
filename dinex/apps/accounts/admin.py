from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

""" ======================= Custom User Admin ======================= """
@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = (
        *UserAdmin.fieldsets,
        (
            "MN Kitchen POS",
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
            "MN Kitchen POS",
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