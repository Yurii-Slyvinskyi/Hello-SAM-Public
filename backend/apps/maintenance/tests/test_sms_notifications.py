import pytest
from rest_framework import status

from apps.maintenance.choices import Priority
from apps.maintenance.models import MaintenanceRequest
from apps.notifications.channels import SmsMessageBuilder, SmsNotificationService
from apps.notifications.models import NotificationLog
from apps.notifications.providers import twilio
from apps.notifications.services import NotificationLogFactory
from apps.notifications.tasks import send_notifications_for_maintenance_request


@pytest.mark.django_db
def test_successful_manager_sms_marks_notification_log_as_sent(
    api_client,
    building,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    send_notifications_for_maintenance_request.run(maintenance_request.id)

    notification_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=building.manager_phone,
    )
    assert notification_log.status == NotificationLog.Status.SENT
    assert notification_log.sent_at is not None
    assert notification_log.provider_message_id == "test-twilio-message-id"
    assert notification_log.error_message == ""


@pytest.mark.django_db
def test_successful_resident_sms_marks_notification_log_as_sent(
    api_client,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    send_notifications_for_maintenance_request.run(maintenance_request.id)

    notification_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=voice_payload["follow_up_phone"],
    )
    assert notification_log.status == NotificationLog.Status.SENT
    assert notification_log.sent_at is not None
    assert notification_log.provider_message_id == "test-twilio-message-id"
    assert notification_log.error_message == ""


@pytest.mark.django_db
def test_twilio_error_marks_sms_notification_log_as_failed(
    api_client,
    monkeypatch,
    voice_payload,
):
    def raise_twilio_error(to_phone, body):
        raise twilio.TwilioError("Twilio unavailable")

    monkeypatch.setattr(twilio, "send_sms", raise_twilio_error)

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    send_notifications_for_maintenance_request.run(maintenance_request.id)

    sms_logs = NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS
    )
    assert sms_logs.count() == 2
    assert all(log.status == NotificationLog.Status.FAILED for log in sms_logs)
    assert all(log.sent_at is None for log in sms_logs)
    assert all(log.provider_message_id == "" for log in sms_logs)
    assert all("Twilio unavailable" in log.error_message for log in sms_logs)


@pytest.mark.django_db
def test_email_notification_log_is_not_processed_by_sms_sender(
    building,
    voice_payload,
):
    maintenance_request = MaintenanceRequest.objects.create(
        building=building,
        call_id=voice_payload["call_id"],
        caller_phone=voice_payload["caller_phone"],
        full_name=voice_payload["full_name"],
        follow_up_phone=voice_payload["follow_up_phone"],
        use_caller_phone_for_follow_up=voice_payload[
            "use_caller_phone_for_follow_up"
        ],
        unit_number=voice_payload["unit_number"],
        issue_type=voice_payload["issue_type"],
        resident_reported_issue=voice_payload["resident_reported_issue"],
        description=voice_payload["description"],
        location_inside_unit=voice_payload["location_inside_unit"],
        ai_priority=voice_payload["ai_priority"],
        backend_priority=voice_payload["ai_priority"],
        final_priority=voice_payload["ai_priority"],
        is_emergency=False,
        emergency_reason="",
        transcript=voice_payload["transcript"],
    )
    NotificationLogFactory().create_for_maintenance_request(maintenance_request)

    SmsNotificationService().send_pending_for_request(maintenance_request)

    email_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.EMAIL
    )
    assert email_log.status == NotificationLog.Status.PENDING
    assert email_log.sent_at is None
    assert email_log.provider_message_id == ""


@pytest.mark.django_db
def test_manager_urgent_sms_matches_required_format(api_client, building, voice_payload):
    voice_payload["full_name"] = "John Smith"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    manager_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=building.manager_phone,
    )
    message_builder = SmsMessageBuilder()
    manager_body = message_builder.build_body(manager_log)

    assert manager_body == (
        "URGENT maintenance at Henday Suites, unit 418, John Smith. "
        "Bathroom sink is leaking heavily under the cabinet. "
        "Follow-up: +17802223333"
    )


@pytest.mark.django_db
def test_manager_sms_uses_final_priority_not_ai_priority(
    api_client,
    building,
    voice_payload,
):
    voice_payload["ai_priority"] = Priority.NORMAL
    voice_payload["description"] = "There is a water leak under the sink."
    voice_payload["resident_reported_issue"] = "There is a water leak."
    voice_payload["transcript"] = "Resident reported a water leak."

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    manager_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=building.manager_phone,
    )
    manager_body = SmsMessageBuilder().build_body(manager_log)

    assert MaintenanceRequest.objects.get().ai_priority == Priority.NORMAL
    assert MaintenanceRequest.objects.get().final_priority == Priority.URGENT
    assert manager_body.startswith("URGENT maintenance")
    assert not manager_body.startswith("NORMAL maintenance")


@pytest.mark.django_db
def test_resident_normal_sms_matches_required_format(api_client, voice_payload):
    voice_payload["ai_priority"] = Priority.NORMAL
    voice_payload["description"] = "Dishwasher button is hard to start."
    voice_payload["resident_reported_issue"] = "My dishwasher is hard to start."
    voice_payload["transcript"] = "Resident reported dishwasher button issue."

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    resident_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=voice_payload["follow_up_phone"],
    )
    resident_body = SmsMessageBuilder().build_body(resident_log)

    assert resident_body == (
        "Your maintenance request for unit 418 has been submitted. "
        "The team has been notified."
    )


@pytest.mark.django_db
def test_resident_urgent_sms_matches_required_format(api_client, voice_payload):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    resident_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=voice_payload["follow_up_phone"],
    )
    resident_body = SmsMessageBuilder().build_body(resident_log)

    assert resident_body == (
        "Your urgent maintenance request for unit 418 has been submitted. "
        "The team has been notified."
    )


@pytest.mark.django_db
def test_resident_emergency_sms_matches_required_format(api_client, voice_payload):
    voice_payload["ai_priority"] = Priority.NORMAL
    voice_payload["description"] = "There is smoke coming from an outlet."
    voice_payload["resident_reported_issue"] = "There is smoke in my unit."
    voice_payload["transcript"] = "Resident reported smoke from an outlet."

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    resident_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=voice_payload["follow_up_phone"],
    )
    resident_body = SmsMessageBuilder().build_body(resident_log)

    assert resident_body == (
        "Your emergency maintenance request for unit 418 has been submitted. "
        "The team has been notified."
    )


@pytest.mark.django_db
def test_sms_bodies_use_purpose_when_manager_and_resident_phone_match(
    api_client,
    building,
    monkeypatch,
    voice_payload,
):
    building.manager_phone = voice_payload["follow_up_phone"]
    building.save(update_fields=["manager_phone"])
    sent_messages = []

    def send_sms(to_phone, body):
        sent_messages.append({"to_phone": to_phone, "body": body})
        return twilio.TwilioSmsResult(message_id=f"message-id-{len(sent_messages)}")

    monkeypatch.setattr(twilio, "send_sms", send_sms)

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    send_notifications_for_maintenance_request.run(maintenance_request.id)

    sms_logs = NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=voice_payload["follow_up_phone"],
    )
    assert sms_logs.count() == 2
    assert set(sms_logs.values_list("purpose", flat=True)) == {
        NotificationLog.Purpose.MANAGER_SMS,
        NotificationLog.Purpose.RESIDENT_SMS,
    }
    assert len(sent_messages) == 2
    assert {message["to_phone"] for message in sent_messages} == {
        voice_payload["follow_up_phone"],
    }
    assert any("Follow-up:" in message["body"] for message in sent_messages)
    assert any("team has been notified" in message["body"] for message in sent_messages)


@pytest.mark.django_db
def test_notification_task_sends_sms_for_new_request(
    api_client,
    building,
    monkeypatch,
    voice_payload,
):
    sent_messages = []

    def send_sms(to_phone, body):
        sent_messages.append({"to_phone": to_phone, "body": body})
        return twilio.TwilioSmsResult(message_id="message-id-123")

    monkeypatch.setattr(twilio, "send_sms", send_sms)

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert len(sent_messages) == 0

    maintenance_request = MaintenanceRequest.objects.get()
    send_notifications_for_maintenance_request.run(maintenance_request.id)

    assert len(sent_messages) == 2
    assert {message["to_phone"] for message in sent_messages} == {
        building.manager_phone,
        voice_payload["follow_up_phone"],
    }


@pytest.mark.django_db
def test_duplicate_call_id_does_not_resend_sms(
    api_client,
    monkeypatch,
    voice_payload,
):
    sent_messages = []

    def send_sms(to_phone, body):
        sent_messages.append(to_phone)
        return twilio.TwilioSmsResult(message_id="message-id-123")

    monkeypatch.setattr(twilio, "send_sms", send_sms)

    first_response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    second_response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    send_notifications_for_maintenance_request.run(maintenance_request.id)
    send_notifications_for_maintenance_request.run(maintenance_request.id)

    assert len(sent_messages) == 2
    assert NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS
    ).count() == 2
