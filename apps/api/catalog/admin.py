from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from .models import Area, Category, Tag, TicketingDomain, Venue


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name_fr", "slug", "parent", "order", "is_active", "is_launch_niche"]
    list_filter = ["is_active", "is_launch_niche"]
    search_fields = ["name_fr", "name_nl", "name_en", "slug"]
    prepopulated_fields = {"slug": ("name_fr",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name_fr", "slug", "is_active"]
    prepopulated_fields = {"slug": ("name_fr",)}


@admin.register(Area)
class AreaAdmin(gis_admin.GISModelAdmin):
    list_display = ["name_fr", "kind", "parent", "postal_codes", "is_active"]
    list_filter = ["kind", "is_active"]
    search_fields = ["name_fr", "name_nl", "slug"]


@admin.register(Venue)
class VenueAdmin(gis_admin.GISModelAdmin):
    list_display = ["name", "postal_code", "city", "area", "organization", "is_active"]
    list_filter = ["city", "is_active"]
    search_fields = ["name", "street"]


@admin.register(TicketingDomain)
class TicketingDomainAdmin(admin.ModelAdmin):
    list_display = ["domain", "status", "note", "updated_at"]
    list_filter = ["status"]
    search_fields = ["domain"]
