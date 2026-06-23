import pytest
from rest_framework import status

from apps.notifications.models import NotificationLog


@pytest.mark.django_db
def test_successful_request_creates_manager_email_notification_log(
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
    assert NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.EMAIL,
        purpose=NotificationLog.Purpose.MANAGER_EMAIL,
        recipient=building.manager_email,
        status=NotificationLog.Status.PENDING,
    ).count() == 1


@pytest.mark.django_db
def test_successful_request_creates_manager_sms_notification_log(
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
    assert NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS,
        purpose=NotificationLog.Purpose.MANAGER_SMS,
        recipient=building.manager_phone,
        status=NotificationLog.Status.PENDING,
    ).count() == 1


@pytest.mark.django_db
def test_successful_request_creates_resident_sms_notification_log_to_follow_up_phone(
    api_client,
    voice_payload,
):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS,
        purpose=NotificationLog.Purpose.RESIDENT_SMS,
        recipient=voice_payload["follow_up_phone"],
        status=NotificationLog.Status.PENDING,
    ).count() == 1


@pytest.mark.django_db
def test_resident_sms_notification_log_uses_caller_phone_when_follow_up_phone_empty(
    api_client,
    voice_payload,
):
    voice_payload["follow_up_phone"] = ""

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS,
        purpose=NotificationLog.Purpose.RESIDENT_SMS,
        recipient=voice_payload["caller_phone"],
        status=NotificationLog.Status.PENDING,
    ).count() == 1


@pytest.mark.django_db
def test_duplicate_call_id_does_not_create_duplicate_notification_logs(
    api_client,
    voice_payload,
):
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
    assert NotificationLog.objects.count() == 3
