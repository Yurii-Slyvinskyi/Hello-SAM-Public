from django.contrib import admin

from .models import MaintenanceRequest


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "building",
        "full_name",
        "unit_number",
        "issue_type",
        "final_priority",
        "status",
        "created_at",
    )
    list_filter = ("building", "final_priority", "status", "created_at")
    search_fields = (
        "full_name",
        "unit_number",
        "caller_phone",
        "follow_up_phone",
        "resident_reported_issue",
        "description",
    )
    readonly_fields = ("transcript", "call_id", "created_at", "updated_at")
    list_editable = ("status",)
    list_select_related = ("building",)
