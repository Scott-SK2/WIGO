from django.contrib import admin

from .models import AuditLog, ModerationDecision, Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["created_at", "category", "event", "organization", "status", "handled_by"]
    list_filter = ["status", "category"]


@admin.register(ModerationDecision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ["created_at", "event", "action", "reason_code", "moderator"]
    list_filter = ["action", "reason_code"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "actor", "action", "target_type", "target_id"]
    list_filter = ["action", "target_type"]
    search_fields = ["target_id", "action"]
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
