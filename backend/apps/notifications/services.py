from .channels import ManagerEmailNotificationService, SmsNotificationService
from .models import NotificationLog


class NotificationLogFactory:
    def create_for_maintenance_request(self, maintenance_request):
        building = maintenance_request.building
        resident_phone = (
            maintenance_request.follow_up_phone or maintenance_request.caller_phone
        )

        notification_specs = [
            {
                "notification_type": NotificationLog.NotificationType.EMAIL,
                "purpose": NotificationLog.Purpose.MANAGER_EMAIL,
                "recipient": building.manager_email,
            },
            {
                "notification_type": NotificationLog.NotificationType.SMS,
                "purpose": NotificationLog.Purpose.MANAGER_SMS,
                "recipient": building.manager_phone,
            },
            {
                "notification_type": NotificationLog.NotificationType.SMS,
                "purpose": NotificationLog.Purpose.RESIDENT_SMS,
                "recipient": resident_phone,
            },
        ]

        notification_logs = []
        for spec in notification_specs:
            notification_log, _created = NotificationLog.objects.get_or_create(
                maintenance_request=maintenance_request,
                purpose=spec["purpose"],
                defaults={
                    "notification_type": spec["notification_type"],
                    "recipient": spec["recipient"],
                },
            )
            notification_logs.append(notification_log)

        return notification_logs


class NotificationOrchestrator:
    def __init__(self, log_factory=None, email_service=None, sms_service=None):
        self.log_factory = log_factory or NotificationLogFactory()
        self.email_service = email_service or ManagerEmailNotificationService()
        self.sms_service = sms_service or SmsNotificationService()

    def create_pending_logs(self, maintenance_request):
        return self.log_factory.create_for_maintenance_request(maintenance_request)

    def send_pending_notifications(self, maintenance_request):
        email_stats = self.email_service.send_pending_for_request(maintenance_request)
        sms_stats = self.sms_service.send_pending_for_request(maintenance_request)
        return _combine_stats(email_stats, sms_stats)

    def retry_notifications(self, notification_log_ids):
        email_stats = self.email_service.retry_logs(notification_log_ids)
        sms_stats = self.sms_service.retry_logs(notification_log_ids)
        return _combine_stats(email_stats, sms_stats)


def _combine_stats(*stats_items):
    combined_stats = {
        "processed": 0,
        "sent": 0,
        "failed": 0,
        "skipped": 0,
    }

    for stats in stats_items:
        for key in combined_stats:
            combined_stats[key] += stats.get(key, 0)

    return combined_stats
