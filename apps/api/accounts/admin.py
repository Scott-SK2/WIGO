from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AccountToken, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "display_name", "language", "status", "trust_level", "is_moderator"]
    list_filter = ["status", "trust_level", "is_moderator", "is_catalog_editor", "language"]
    search_fields = ["email", "display_name"]
    readonly_fields = ["last_login", "created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profil", {"fields": ("display_name", "language", "email_verified_at")}),
        ("Statut et confiance", {"fields": ("status", "suspended_until", "trust_level")}),
        (
            "Rôles",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "is_moderator",
                    "is_catalog_editor",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)
    filter_horizontal = ("groups", "user_permissions", "followed_areas", "followed_categories")


@admin.register(AccountToken)
class AccountTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "kind", "expires_at", "used_at"]
    list_filter = ["kind"]
