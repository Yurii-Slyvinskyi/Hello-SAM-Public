import logging

from django.db import transaction
from django.utils import timezone

from apps.notifications.models import NotificationLog


logger = logging.getLogger(__name__)


class NotificationDeliveryService:
    notification_type = None

    def send_pending_for_request(self, maintenance_request):
        notification_logs = self.get_logs_for_request(
            maintenance_request=maintenance_request,
            eligible_statuses=[NotificationLog.Status.PENDING],
        )

        return self.process_logs(
            notification_logs=notification_logs,
            eligible_statuses=[NotificationLog.Status.PENDING],
        )

    def retry_logs(self, notification_log_ids):
        notification_logs = self.get_logs_by_ids(
            notification_log_ids=notification_log_ids,
            eligible_statuses=[
                NotificationLog.Status.PENDING,
                NotificationLog.Status.FAILED,
            ],
        )

        return self.process_logs(
            notification_logs=notification_logs,
            eligible_statuses=[
                NotificationLog.Status.PENDING,
                NotificationLog.Status.FAILED,
            ],
        )

    def get_logs_for_request(self, maintenance_request, eligible_statuses):
        return NotificationLog.objects.filter(
            maintenance_request=maintenance_request,
            notification_type=self.notification_type,
            status__in=eligible_statuses,
        ).select_related("maintenance_request", "maintenance_request__building")

    def get_logs_by_ids(self, notification_log_ids, eligible_statuses):
        return NotificationLog.objects.filter(
            id__in=notification_log_ids,
            notification_type=self.notification_type,
            status__in=eligible_statuses,
        ).select_related("maintenance_request", "maintenance_request__building")

    def process_logs(self, notification_logs, eligible_statuses):
        stats = {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0,
        }

        for notification_log in notification_logs:
            claimed_log = self.claim(notification_log.id, eligible_statuses)
            if claimed_log is None:
                stats["skipped"] += 1
                continue

            stats["processed"] += 1
            processed_log = self.send_claimed(claimed_log)
            if processed_log.status == NotificationLog.Status.SENT:
                stats["sent"] += 1
            elif processed_log.status == NotificationLog.Status.FAILED:
                stats["failed"] += 1

        return stats

    def claim(self, notification_log_id, eligible_statuses):
        with transaction.atomic():
            notification_log = (
                NotificationLog.objects.select_for_update()
                .select_related("maintenance_request", "maintenance_request__building")
                .filter(
                    id=notification_log_id,
                    notification_type=self.notification_type,
                    status__in=eligible_statuses,
                )
                .first()
            )

            if notification_log is None:
                return None

            notification_log.status = NotificationLog.Status.PROCESSING
            notification_log.attempt_count += 1
            notification_log.last_attempt_at = timezone.now()
            notification_log.save(
                update_fields=[
                    "status",
                    "attempt_count",
                    "last_attempt_at",
                ]
            )

        return notification_log

    def send_claimed(self, notification_log):
        if notification_log.status != NotificationLog.Status.PROCESSING:
            return notification_log

        try:
            result = self.deliver(notification_log)
        except Exception as exc:
            self.mark_failed(notification_log, exc)
            return notification_log

        self.mark_sent(notification_log, result)
        return notification_log

    def deliver(self, notification_log):
        raise NotImplementedError

    def mark_sent(self, notification_log, result):
        notification_log.status = NotificationLog.Status.SENT
        notification_log.sent_at = timezone.now()
        notification_log.provider_message_id = getattr(result, "message_id", "")
        notification_log.error_message = ""
        notification_log.save(
            update_fields=[
                "status",
                "sent_at",
                "provider_message_id",
                "error_message",
            ]
        )

    def mark_failed(self, notification_log, error):
        logger.exception(
            "notification_delivery_failed notification_log_id=%s "
            "notification_type=%s maintenance_request_id=%s",
            notification_log.id,
            notification_log.notification_type,
            notification_log.maintenance_request_id,
        )
        notification_log.status = NotificationLog.Status.FAILED
        notification_log.error_message = str(error)
        notification_log.sent_at = None
        notification_log.provider_message_id = ""
        notification_log.save(
            update_fields=[
                "status",
                "error_message",
                "sent_at",
                "provider_message_id",
            ]
        )
