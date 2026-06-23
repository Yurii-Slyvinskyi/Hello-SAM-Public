from django.contrib import admin

from .models import Building


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "maintenance_phone_number",
        "office_phone_number",
        "is_active",
    )
    search_fields = (
        "name",
        "address",
        "maintenance_phone_number",
        "office_phone_number",
        "manager_phone",
    )
    list_filter = ("company", "is_active")
    readonly_fields = ("created_at",)
    list_select_related = ("company",)
