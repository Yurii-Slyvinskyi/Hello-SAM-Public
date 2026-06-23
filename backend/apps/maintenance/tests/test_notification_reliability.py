import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import IntegrityError, transaction
from django.test import RequestFactory
from rest_framework import status

from apps.maintenance.models import MaintenanceRequest
from apps.notifications.admin import NotificationLogAdmin
from apps.notifications.models import NotificationLog
from apps.notifications.providers import postmark, twilio
from apps.notifications.channels import ManagerEmailNotificationService
from apps.notifications.services import NotificationLogFactory
from apps.notifications.tasks import (
    retry_notification_logs,
    send_notifications_for_maintenance_request,
)


@pytest.mark.django_db
def test_unique_constraint_prevents_duplicate_log_purpose(api_client, voice_payload):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    existing_log = NotificationLog.objects.get(
        purpose=NotificationLog.Purpose.MANAGER_EMAIL
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            NotificationLog.objects.create(
                maintenance_request=maintenance_request,
                notification_type=existing_log.notification_type,
                purpose=existing_log.purpose,
                recipient=existing_log.recipient,
            )


@pytest.mark.django_db
def test_notification_factory_does_not_create_duplicate_logs(api_client, voice_payload):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    NotificationLogFactory().create_for_maintenance_request(maintenance_request)

    assert NotificationLog.objects.count() == 3
    assert set(NotificationLog.objects.values_list("purpose", flat=True)) == {
        NotificationLog.Purpose.MANAGER_EMAIL,
        NotificationLog.Purpose.MANAGER_SMS,
        NotificationLog.Purpose.RESIDENT_SMS,
    }


@pytest.mark.django_db
def test_pending_notification_is_claimed_before_provider_delivery(
    api_client,
    monkeypatch,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    email_log = NotificationLog.objects.get(
        purpose=NotificationLog.Purpose.MANAGER_EMAIL
    )
    statuses_seen_by_provider = []

    def send_email(to_email, subject, text_body):
        email_log.refresh_from_db()
        statuses_seen_by_provider.append(email_log.status)
        return postmark.PostmarkEmailResult(message_id="claimed-message-id")

    monkeypatch.setattr(postmark, "send_email", send_email)

    send_notifications_for_maintenance_request.run(MaintenanceRequest.objects.get().id)

    email_log.refresh_from_db()
    assert statuses_seen_by_provider == [NotificationLog.Status.PROCESSING]
    assert email_log.status == NotificationLog.Status.SENT
    assert email_log.attempt_count == 1
    assert email_log.last_attempt_at is not None


@pytest.mark.django_db
def test_sent_notification_is_not_resent(api_client, monkeypatch, voice_payload):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    sent_email_count = 0

    def send_email(to_email, subject, text_body):
        nonlocal sent_email_count
        sent_email_count += 1
        return postmark.PostmarkEmailResult(message_id=f"email-{sent_email_count}")

    monkeypatch.setattr(postmark, "send_email", send_email)

    maintenance_request = MaintenanceRequest.objects.get()
    send_notifications_for_maintenance_request.run(maintenance_request.id)
    send_notifications_for_maintenance_request.run(maintenance_request.id)

    email_log = NotificationLog.objects.get(
        purpose=NotificationLog.Purpose.MANAGER_EMAIL
    )
    assert sent_email_count == 1
    assert email_log.status == NotificationLog.Status.SENT
    assert email_log.attempt_count == 1


@pytest.mark.django_db
def test_processing_notification_is_not_processed_by_normal_task(
    api_client,
    monkeypatch,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    email_log = NotificationLog.objects.get(
        purpose=NotificationLog.Purpose.MANAGER_EMAIL
    )
    email_log.status = NotificationLog.Status.PROCESSING
    email_log.save(update_fields=["status"])
    sent_email_count = 0

    def send_email(to_email, subject, text_body):
        nonlocal sent_email_count
        sent_email_count += 1
        return postmark.PostmarkEmailResult(message_id="unexpected")

    monkeypatch.setattr(postmark, "send_email", send_email)

    send_notifications_for_maintenance_request.run(MaintenanceRequest.objects.get().id)

    email_log.refresh_from_db()
    assert sent_email_count == 0
    assert email_log.status == NotificationLog.Status.PROCESSING
    assert email_log.attempt_count == 0


@pytest.mark.django_db
def test_processing_notification_is_skipped_by_explicit_retry(
    api_client,
    monkeypatch,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    email_log = NotificationLog.objects.get(
        purpose=NotificationLog.Purpose.MANAGER_EMAIL
    )
    email_log.status = NotificationLog.Status.PROCESSING
    email_log.save(update_fields=["status"])
    sent_email_count = 0

    def send_email(to_email, subject, text_body):
        nonlocal sent_email_count
        sent_email_count += 1
        return postmark.PostmarkEmailResult(message_id="unexpected")

    monkeypatch.setattr(postmark, "send_email", send_email)

    retry_notification_logs.run([email_log.id])

    email_log.refresh_from_db()
    assert sent_email_count == 0
    assert email_log.status == NotificationLog.Status.PROCESSING
    assert email_log.attempt_count == 0


@pytest.mark.django_db
def test_sent_notification_is_skipped_by_explicit_retry(
    api_client,
    monkeypatch,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    email_log = NotificationLog.objects.get(
        purpose=NotificationLog.Purpose.MANAGER_EMAIL
    )
    email_log.status = NotificationLog.Status.SENT
    email_log.provider_message_id = "already-sent-message-id"
    email_log.save(update_fields=["status", "provider_message_id"])
    notification_log_count = NotificationLog.objects.count()
    sent_email_count = 0

    def send_email(to_email, subject, text_body):
        nonlocal sent_email_count
        sent_email_count += 1
        return postmark.PostmarkEmailResult(message_id="unexpected")

    monkeypatch.setattr(postmark, "send_email", send_email)

    result = retry_notification_logs.run([email_log.id])

    email_log.refresh_from_db()
    assert result["processed"] == 0
    assert result["sent"] == 0
    assert result["failed"] == 0
    assert sent_email_count == 0
    assert email_log.status == NotificationLog.Status.SENT
    assert email_log.provider_message_id == "already-sent-message-id"
    assert NotificationLog.objects.count() == notification_log_count


@pytest.mark.django_db
def test_second_claim_attempt_cannot_send_same_pending_notification(
    api_client,
    monkeypatch,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    email_log = NotificationLog.objects.get(
        purpose=NotificationLog.Purpose.MANAGER_EMAIL
    )
    service = ManagerEmailNotificationService()
    sent_email_count = 0

    def send_email(to_email, subject, text_body):
        nonlocal sent_email_count
        sent_email_count += 1
        return postmark.PostmarkEmailResult(message_id="claimed-message-id")

    monkeypatch.setattr(postmark, "send_email", send_email)

    first_claim = service.claim(email_log.id, [NotificationLog.Status.PENDING])
    second_claim = service.claim(email_log.id, [NotificationLog.Status.PENDING])

    assert first_claim is not None
    assert second_claim is None

    service.send_claimed(first_claim)

    email_log.refresh_from_db()
    assert sent_email_count == 1
    assert email_log.status == NotificationLog.Status.SENT
    assert email_log.provider_message_id == "claimed-message-id"
    assert email_log.attempt_count == 1


@pytest.mark.django_db
def test_provider_failure_does_not_stop_other_notifications(
    api_client,
    monkeypatch,
    voice_payload,
):
    def raise_postmark_error(to_email, subject, text_body):
        raise postmark.PostmarkError("Postmark unavailable")

    sent_sms_recipients = []

    def send_sms(to_phone, body):
        sent_sms_recipients.append(to_phone)
        return twilio.TwilioSmsResult(message_id=f"sms-{len(sent_sms_recipients)}")

    monkeypatch.setattr(postmark, "send_email", raise_postmark_error)
    monkeypatch.setattr(twilio, "send_sms", send_sms)

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    send_notifications_for_maintenance_request.run(MaintenanceRequest.objects.get().id)

    email_log = NotificationLog.objects.get(
        purpose=NotificationLog.Purpose.MANAGER_EMAIL
    )
    sms_logs = NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS
    )

    assert email_log.status == NotificationLog.Status.FAILED
    assert "Postmark unavailable" in email_log.error_message
    assert sms_logs.count() == 2
    assert all(log.status == NotificationLog.Status.SENT for log in sms_logs)
    assert len(sent_sms_recipients) == 2


@pytest.mark.django_db
def test_failed_notification_can_be_retried_successfully(
    api_client,
    monkeypatch,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    email_log = NotificationLog.objects.get(
        purpose=NotificationLog.Purpose.MANAGER_EMAIL
    )
    email_log.status = NotificationLog.Status.FAILED
    email_log.error_message = "Previous failure"
    email_log.save(update_fields=["status", "error_message"])

    def send_email(to_email, subject, text_body):
        return postmark.PostmarkEmailResult(message_id="retry-message-id")

    monkeypatch.setattr(postmark, "send_email", send_email)

    retry_notification_logs.run([email_log.id])

    email_log.refresh_from_db()
    assert email_log.status == NotificationLog.Status.SENT
    assert email_log.provider_message_id == "retry-message-id"
    assert email_log.error_message == ""
    assert email_log.sent_at is not None
    assert email_log.attempt_count == 1
    assert email_log.last_attempt_at is not None


@pytest.mark.django_db
def test_pending_notification_left_after_missed_enqueue_can_be_retried(
    api_client,
    monkeypatch,
    voice_payload,
):
    sent_messages = []

    def send_sms(to_phone, body):
        sent_messages.append(to_phone)
        return twilio.TwilioSmsResult(message_id=f"sms-{len(sent_messages)}")

    monkeypatch.setattr(twilio, "send_sms", send_sms)

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert NotificationLog.objects.filter(status=NotificationLog.Status.PENDING).count() == 3

    retry_notification_logs.run(
        list(NotificationLog.objects.values_list("id", flat=True))
    )

    assert NotificationLog.objects.filter(status=NotificationLog.Status.SENT).count() == 3
    assert len(sent_messages) == 2


@pytest.mark.django_db
def test_admin_retry_enqueue_failure_leaves_logs_unchanged(
    api_client,
    monkeypatch,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED

    def raise_enqueue_error(notification_log_ids):
        raise RuntimeError("Redis unavailable")

    monkeypatch.setattr(retry_notification_logs, "delay", raise_enqueue_error)
    logged_messages = []
    monkeypatch.setattr(
        "apps.notifications.admin.logger.exception",
        lambda message, *args: logged_messages.append(message),
    )

    request = RequestFactory().post("/")
    request.session = {}
    request._messages = FallbackStorage(request)
    model_admin = NotificationLogAdmin(NotificationLog, AdminSite())

    model_admin.retry_selected_pending_or_failed_notifications(
        request,
        NotificationLog.objects.all(),
    )

    assert NotificationLog.objects.filter(status=NotificationLog.Status.PENDING).count() == 3
    assert logged_messages == [
        "notification_retry_enqueue_failed notification_log_count=%s"
    ]
