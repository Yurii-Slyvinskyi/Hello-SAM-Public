from django.db import models


class NotificationLog(models.Model):
    class NotificationType(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"

    class Purpose(models.TextChoices):
        MANAGER_EMAIL = "manager_email", "Manager email"
        MANAGER_SMS = "manager_sms", "Manager SMS"
        RESIDENT_SMS = "resident_sms", "Resident SMS"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    maintenance_request = models.ForeignKey(
        "maintenance.MaintenanceRequest",
        related_name="notification_logs",
        on_delete=models.CASCADE,
    )
    notification_type = models.CharField(
        max_length=16,
        choices=NotificationType.choices,
    )
    purpose = models.CharField(
        max_length=32,
        choices=Purpose.choices,
        blank=True,
        default="",
    )
    recipient = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["maintenance_request", "purpose"],
                name="unique_notification_log_purpose_per_request",
            )
        ]

    def __str__(self):
        return f"{self.notification_type} to {self.recipient}"
