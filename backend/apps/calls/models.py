from django.db import models


class CallLog(models.Model):
    building = models.ForeignKey(
        "buildings.Building",
        related_name="call_logs",
        on_delete=models.PROTECT,
    )
    call_id = models.CharField(max_length=255, db_index=True)
    called_number = models.CharField(max_length=32)
    caller_phone = models.CharField(max_length=32)
    transcript = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.call_id
