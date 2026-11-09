from django.contrib import admin

from .models import (
    ImportRun,
    ImportSource,
    NewsletterSubscription,
    WeekendSelection,
    WeekendSelectionItem,
)


@admin.register(NewsletterSubscription)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ["email", "language", "area", "status", "consent_at", "confirmed_at"]
    list_filter = ["status", "language"]
    search_fields = ["email"]
    readonly_fields = ["confirm_token", "unsubscribe_token"]


class SelectionItemInline(admin.TabularInline):
    model = WeekendSelectionItem
    extra = 0
    autocomplete_fields = ["event"]


@admin.register(WeekendSelection)
class SelectionAdmin(admin.ModelAdmin):
    list_display = ["week_start", "title", "send_status", "sent_at", "recipients_count", "editor"]
    inlines = [SelectionItemInline]


class RunInline(admin.TabularInline):
    model = ImportRun
    extra = 0
    readonly_fields = [
        "started_at",
        "finished_at",
        "status",
        "created_count",
        "updated_count",
        "skipped_count",
        "log",
    ]


@admin.register(ImportSource)
class ImportSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "licence", "is_active", "last_run_at"]
    inlines = [RunInline]
