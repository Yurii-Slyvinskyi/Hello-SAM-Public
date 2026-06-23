from apps.notifications.models import NotificationLog
from apps.notifications.providers.twilio import TwilioSmsProvider

from .delivery import NotificationDeliveryService
from .messages import SmsMessageBuilder


class SmsNotificationService(NotificationDeliveryService):
    notification_type = NotificationLog.NotificationType.SMS

    def __init__(self, provider=None, message_builder=None):
        self.provider = provider or TwilioSmsProvider()
        self.message_builder = message_builder or SmsMessageBuilder()

    def deliver(self, notification_log):
        return self.provider.send(
            to_phone=notification_log.recipient,
            body=self.message_builder.build_body(notification_log),
        )
