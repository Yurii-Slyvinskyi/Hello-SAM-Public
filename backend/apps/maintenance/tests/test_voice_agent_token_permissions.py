import pytest
from rest_framework import status

from apps.calls.models import CallLog
from apps.maintenance.models import MaintenanceRequest
from apps.notifications.models import NotificationLog


@pytest.mark.django_db
def test_missing_voice_agent_token_returns_403(
    unauthenticated_api_client,
    voice_payload,
):
    response = unauthenticated_api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_invalid_voice_agent_token_returns_403(
    unauthenticated_api_client,
    voice_payload,
):
    response = unauthenticated_api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
        HTTP_X_VOICE_AGENT_TOKEN="wrong-token",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_valid_voice_agent_token_allows_successful_request(
    unauthenticated_api_client,
    voice_payload,
):
    response = unauthenticated_api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
        HTTP_X_VOICE_AGENT_TOKEN="test-token",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["success"] is True


@pytest.mark.django_db
def test_missing_voice_agent_token_does_not_create_records_or_queue_task(
    unauthenticated_api_client,
    mock_send_notifications_task_delay,
    voice_payload,
):
    response = unauthenticated_api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert MaintenanceRequest.objects.count() == 0
    assert CallLog.objects.count() == 0
    assert NotificationLog.objects.count() == 0
    assert mock_send_notifications_task_delay == []


@pytest.mark.django_db
def test_invalid_voice_agent_token_does_not_create_records_or_queue_task(
    unauthenticated_api_client,
    mock_send_notifications_task_delay,
    voice_payload,
):
    response = unauthenticated_api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
        HTTP_X_VOICE_AGENT_TOKEN="wrong-token",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert MaintenanceRequest.objects.count() == 0
    assert CallLog.objects.count() == 0
    assert NotificationLog.objects.count() == 0
    assert mock_send_notifications_task_delay == []


@pytest.mark.django_db
def test_empty_configured_voice_agent_token_denies_request(
    settings,
    unauthenticated_api_client,
    voice_payload,
):
    settings.VOICE_AGENT_TOKEN = ""

    response = unauthenticated_api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
        HTTP_X_VOICE_AGENT_TOKEN="test-token",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
