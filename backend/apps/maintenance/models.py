from django.db import models

from apps.common.validators import validate_e164_phone_number

from .choices import IssueType, Priority


class MaintenanceRequest(models.Model):
    building = models.ForeignKey(
        "buildings.Building",
        related_name="maintenance_requests",
        on_delete=models.PROTECT,
    )
    call_id = models.CharField(max_length=255, unique=True)
    caller_phone = models.CharField(
        max_length=32,
        validators=[validate_e164_phone_number],
    )
    full_name = models.CharField(max_length=255)
    follow_up_phone = models.CharField(
        max_length=32,
        blank=True,
        validators=[validate_e164_phone_number],
    )
    use_caller_phone_for_follow_up = models.BooleanField(default=True)
    unit_number = models.CharField(max_length=64)
    issue_type = models.CharField(max_length=64, choices=IssueType.choices)
    resident_reported_issue = models.TextField()
    description = models.TextField()
    location_inside_unit = models.CharField(max_length=255)
    ai_priority = models.CharField(
        max_length=16,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    backend_priority = models.CharField(
        max_length=16,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    final_priority = models.CharField(
        max_length=16,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    is_emergency = models.BooleanField(default=False)
    emergency_reason = models.TextField(blank=True)
    transcript = models.TextField()
    status = models.CharField(max_length=32, default="new")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.building} unit {self.unit_number} - {self.final_priority}"
