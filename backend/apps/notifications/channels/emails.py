from apps.notifications.models import NotificationLog
from apps.notifications.providers.postmark import PostmarkEmailProvider

from .delivery import NotificationDeliveryService
from .messages import ManagerEmailMessageBuilder


class ManagerEmailNotificationService(NotificationDeliveryService):
    notification_type = NotificationLog.NotificationType.EMAIL

    def __init__(self, provider=None, message_builder=None):
        self.provider = provider or PostmarkEmailProvider()
        self.message_builder = message_builder or ManagerEmailMessageBuilder()

    def deliver(self, notification_log):
        maintenance_request = notification_log.maintenance_request
        return self.provider.send(
            to_email=notification_log.recipient,
            subject=self.message_builder.build_subject(maintenance_request),
            text_body=self.message_builder.build_body(maintenance_request),
        )
