from django.contrib import admin

from .models import Event, EventDailyStat, EventMedia, EventOccurrence, Favorite


class OccurrenceInline(admin.TabularInline):
    model = EventOccurrence
    extra = 0


class MediaInline(admin.TabularInline):
    model = EventMedia
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "status",
        "primary_category",
        "venue",
        "organization",
        "owner_user",
        "source",
        "updated_at",
    ]
    list_filter = ["status", "format", "pricing_type", "source", "visibility", "primary_category"]
    search_fields = ["title", "slug", "description"]
    autocomplete_fields = ["venue", "organization", "owner_user"]
    readonly_fields = ["slug", "search_vector", "created_at", "updated_at"]
    filter_horizontal = ["secondary_categories", "tags"]
    inlines = [OccurrenceInline, MediaInline]
    date_hierarchy = "created_at"


@admin.register(EventOccurrence)
class OccurrenceAdmin(admin.ModelAdmin):
    list_display = ["event", "starts_at", "ends_at", "timezone", "status"]
    list_filter = ["status"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "event", "created_at"]


@admin.register(EventDailyStat)
class StatAdmin(admin.ModelAdmin):
    list_display = ["event", "date", "views", "ticket_clicks", "favorites_added", "calendar_adds"]
