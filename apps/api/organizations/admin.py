from django.contrib import admin

from .models import Organization, OrganizationMember, OwnershipClaim


class MemberInline(admin.TabularInline):
    model = OrganizationMember
    extra = 0
    autocomplete_fields = ["user"]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "type",
        "verification_status",
        "trust_level",
        "is_claimable",
        "is_suspended",
    ]
    list_filter = ["type", "verification_status", "trust_level", "is_claimable", "is_suspended"]
    search_fields = ["name", "slug", "bce_number"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MemberInline]


@admin.register(OwnershipClaim)
class OwnershipClaimAdmin(admin.ModelAdmin):
    list_display = ["organization", "claimant", "status", "created_at", "decided_by"]
    list_filter = ["status"]
