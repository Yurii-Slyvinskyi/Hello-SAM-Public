from django.contrib import admin

from .models import CallLog


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = (
        "building",
        "call_id",
        "called_number",
        "caller_phone",
        "created_at",
    )
    search_fields = ("call_id", "called_number", "caller_phone", "transcript")
    readonly_fields = ("created_at",)
    list_select_related = ("building",)
