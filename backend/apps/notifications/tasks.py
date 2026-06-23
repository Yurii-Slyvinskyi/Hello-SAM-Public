import logging

from celery import shared_task

from apps.maintenance.models import MaintenanceRequest

from .services import NotificationOrchestrator


logger = logging.getLogger(__name__)


@shared_task(name="notifications.send_notifications_for_maintenance_request")
def send_notifications_for_maintenance_request(maintenance_request_id):
    logger.info(
        "notification_task_started maintenance_request_id=%s",
        maintenance_request_id,
    )

    try:
        maintenance_request = MaintenanceRequest.objects.get(
            id=maintenance_request_id
        )
    except MaintenanceRequest.DoesNotExist:
        logger.warning(
            "notification_task_missing_maintenance_request maintenance_request_id=%s",
            maintenance_request_id,
        )
        return {
            "success": False,
            "reason": "maintenance_request_not_found",
        }

    try:
        stats = NotificationOrchestrator().send_pending_notifications(
            maintenance_request
        )
    except Exception:
        logger.exception(
            "notification_task_failed maintenance_request_id=%s",
            maintenance_request_id,
        )
        raise

    logger.info(
        "notification_task_succeeded maintenance_request_id=%s processed=%s "
        "sent=%s failed=%s skipped=%s",
        maintenance_request.id,
        stats["processed"],
        stats["sent"],
        stats["failed"],
        stats["skipped"],
    )
    return {
        "success": True,
        "maintenance_request_id": maintenance_request.id,
        **stats,
    }


@shared_task(name="notifications.retry_notification_logs")
def retry_notification_logs(notification_log_ids):
    notification_log_ids = list(notification_log_ids)
    logger.info(
        "notification_retry_task_started notification_log_count=%s",
        len(notification_log_ids),
    )

    try:
        stats = NotificationOrchestrator().retry_notifications(notification_log_ids)
    except Exception:
        logger.exception(
            "notification_retry_task_failed notification_log_count=%s",
            len(notification_log_ids),
        )
        raise

    logger.info(
        "notification_retry_task_succeeded processed=%s sent=%s failed=%s skipped=%s",
        stats["processed"],
        stats["sent"],
        stats["failed"],
        stats["skipped"],
    )
    return {
        "success": True,
        **stats,
    }
