import logging

from django.contrib import admin
from django.contrib import messages

from .models import NotificationLog
from .tasks import retry_notification_logs


logger = logging.getLogger(__name__)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        "maintenance_request",
        "notification_type",
        "purpose",
        "recipient",
        "status",
        "attempt_count",
        "created_at",
        "last_attempt_at",
        "sent_at",
    )
    list_filter = ("notification_type", "purpose", "status")
    search_fields = ("recipient", "provider_message_id", "error_message")
    readonly_fields = ("attempt_count", "last_attempt_at", "created_at", "sent_at")
    list_select_related = ("maintenance_request",)
    actions = ("retry_selected_pending_or_failed_notifications",)

    @admin.action(description="Retry selected pending or failed notifications")
    def retry_selected_pending_or_failed_notifications(self, request, queryset):
        eligible_statuses = [
            NotificationLog.Status.PENDING,
            NotificationLog.Status.FAILED,
        ]
        selected_count = queryset.count()
        eligible_ids = list(
            queryset.filter(status__in=eligible_statuses).values_list(
                "id",
                flat=True,
            )
        )
        skipped_count = selected_count - len(eligible_ids)

        if not eligible_ids:
            self.message_user(
                request,
                "No pending or failed notifications were selected for retry.",
                level=messages.WARNING,
            )
            return

        try:
            retry_notification_logs.delay(eligible_ids)
        except Exception:
            logger.exception(
                "notification_retry_enqueue_failed notification_log_count=%s",
                len(eligible_ids),
            )
            self.message_user(
                request,
                "Could not queue notification retry. Try again later.",
                level=messages.ERROR,
            )
            return

        self.message_user(
            request,
            (
                f"Queued {len(eligible_ids)} notification(s) for retry. "
                f"Skipped {skipped_count} notification(s)."
            ),
            level=messages.SUCCESS,
        )
