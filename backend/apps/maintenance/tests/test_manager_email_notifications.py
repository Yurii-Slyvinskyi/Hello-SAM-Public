import pytest
from rest_framework import status

from apps.maintenance.choices import Priority
from apps.maintenance.models import MaintenanceRequest
from apps.notifications.channels import (
    ManagerEmailMessageBuilder,
    ManagerEmailNotificationService,
)
from apps.notifications.models import NotificationLog
from apps.notifications.providers import postmark
from apps.notifications.services import NotificationLogFactory
from apps.notifications.tasks import send_notifications_for_maintenance_request


@pytest.mark.django_db
def test_successful_postmark_send_marks_manager_email_notification_as_sent(
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
        notification_type=NotificationLog.NotificationType.EMAIL
    )
    assert notification_log.status == NotificationLog.Status.SENT
    assert notification_log.sent_at is not None
    assert notification_log.provider_message_id == "test-postmark-message-id"
    assert notification_log.error_message == ""


@pytest.mark.django_db
def test_postmark_error_marks_manager_email_notification_as_failed(
    api_client,
    monkeypatch,
    voice_payload,
):
    def raise_postmark_error(to_email, subject, text_body):
        raise postmark.PostmarkError("Postmark unavailable")

    monkeypatch.setattr(postmark, "send_email", raise_postmark_error)

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    send_notifications_for_maintenance_request.run(maintenance_request.id)

    notification_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.EMAIL
    )
    assert notification_log.status == NotificationLog.Status.FAILED
    assert notification_log.sent_at is None
    assert notification_log.provider_message_id == ""
    assert "Postmark unavailable" in notification_log.error_message


@pytest.mark.django_db
def test_sms_notification_logs_are_not_processed_by_email_sender(
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

    ManagerEmailNotificationService().send_pending_for_request(maintenance_request)

    sms_logs = NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS
    )
    assert sms_logs.count() == 2
    assert all(log.status == NotificationLog.Status.PENDING for log in sms_logs)
    assert all(log.sent_at is None for log in sms_logs)
    assert all(log.provider_message_id == "" for log in sms_logs)


@pytest.mark.django_db
def test_manager_urgent_email_subject_matches_required_format(
    api_client,
    voice_payload,
):
    voice_payload["full_name"] = "John Smith"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    message_builder = ManagerEmailMessageBuilder()
    subject = message_builder.build_subject(maintenance_request)

    assert subject == "[URGENT] Henday Suites - Unit 418 Maintenance Request"


@pytest.mark.django_db
def test_manager_emergency_email_subject_includes_emergency_prefix(
    api_client,
    voice_payload,
):
    voice_payload["description"] = "There is a gas smell near the stove."
    voice_payload["resident_reported_issue"] = "There is a gas smell near the stove."
    voice_payload["transcript"] = "Resident reported a gas smell."
    voice_payload["ai_priority"] = Priority.NORMAL

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    subject = ManagerEmailMessageBuilder().build_subject(maintenance_request)

    assert subject == "[EMERGENCY] Henday Suites - Unit 418 Maintenance Request"


@pytest.mark.django_db
def test_manager_normal_email_subject_has_no_priority_prefix(
    api_client,
    voice_payload,
):
    voice_payload["description"] = "Dishwasher button is hard to start."
    voice_payload["resident_reported_issue"] = "My dishwasher is hard to start."
    voice_payload["transcript"] = "Resident reported dishwasher button issue."
    voice_payload["ai_priority"] = Priority.NORMAL

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    subject = ManagerEmailMessageBuilder().build_subject(maintenance_request)

    assert subject == "Henday Suites - Unit 418 Maintenance Request"


@pytest.mark.django_db
def test_manager_email_body_matches_required_format(
    api_client,
    voice_payload,
):
    voice_payload["full_name"] = "John Smith"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    message_builder = ManagerEmailMessageBuilder()
    body = message_builder.build_body(maintenance_request)

    assert body == "\n".join(
        [
            "New maintenance request",
            "",
            "Building: Henday Suites",
            "Unit: 418",
            "Resident: John Smith",
            "Priority: urgent",
            "Issue type: plumbing",
            "",
            "Resident reported issue:",
            "There is water coming from under my bathroom sink.",
            "",
            "Description:",
            "Bathroom sink is leaking heavily under the cabinet.",
            "",
            "Location:",
            "Bathroom",
            "",
            "Follow-up phone: +17802223333",
            "Caller phone: +17802223333",
        ]
    )


@pytest.mark.django_db
def test_notification_task_sends_manager_email_for_new_request(
    api_client,
    building,
    monkeypatch,
    voice_payload,
):
    sent_emails = []

    def send_email(to_email, subject, text_body):
        sent_emails.append(
            {
                "to_email": to_email,
                "subject": subject,
                "text_body": text_body,
            }
        )
        return postmark.PostmarkEmailResult(message_id="message-id-123")

    monkeypatch.setattr(postmark, "send_email", send_email)

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert len(sent_emails) == 0

    maintenance_request = MaintenanceRequest.objects.get()
    send_notifications_for_maintenance_request.run(maintenance_request.id)

    assert len(sent_emails) == 1
    assert sent_emails[0]["to_email"] == building.manager_email


@pytest.mark.django_db
def test_duplicate_call_id_does_not_resend_manager_email(
    api_client,
    monkeypatch,
    voice_payload,
):
    sent_emails = []

    def send_email(to_email, subject, text_body):
        sent_emails.append(to_email)
        return postmark.PostmarkEmailResult(message_id="message-id-123")

    monkeypatch.setattr(postmark, "send_email", send_email)

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

    assert len(sent_emails) == 1
    assert NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.EMAIL
    ).count() == 1
