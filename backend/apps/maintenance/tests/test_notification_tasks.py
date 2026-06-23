import pytest
from django.db import transaction
from rest_framework import status

from apps.maintenance.models import MaintenanceRequest
from apps.maintenance.services import create_maintenance_request_from_voice_payload
from apps.notifications.models import NotificationLog
from apps.notifications.tasks import send_notifications_for_maintenance_request


@pytest.mark.django_db
def test_new_post_request_queues_notification_task(
    api_client,
    django_capture_on_commit_callbacks,
    mock_send_notifications_task_delay,
    voice_payload,
):
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            "/api/voice/maintenance-requests/",
            voice_payload,
            format="json",
        )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    assert mock_send_notifications_task_delay == [maintenance_request.id]


@pytest.mark.django_db
def test_duplicate_call_id_does_not_queue_another_notification_task(
    api_client,
    django_capture_on_commit_callbacks,
    mock_send_notifications_task_delay,
    voice_payload,
):
    with django_capture_on_commit_callbacks(execute=True):
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
    assert mock_send_notifications_task_delay == [maintenance_request.id]


@pytest.mark.django_db
def test_notification_task_calls_orchestrator_for_maintenance_request(
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

    maintenance_request = MaintenanceRequest.objects.get()
    processed_request_ids = []

    class FakeNotificationOrchestrator:
        def send_pending_notifications(self, maintenance_request):
            processed_request_ids.append(maintenance_request.id)
            return {
                "processed": 0,
                "sent": 0,
                "failed": 0,
                "skipped": 0,
            }

    monkeypatch.setattr(
        "apps.notifications.tasks.NotificationOrchestrator",
        FakeNotificationOrchestrator,
    )

    result = send_notifications_for_maintenance_request.run(maintenance_request.id)

    assert processed_request_ids == [maintenance_request.id]
    assert result == {
        "success": True,
        "maintenance_request_id": maintenance_request.id,
        "processed": 0,
        "sent": 0,
        "failed": 0,
        "skipped": 0,
    }


@pytest.mark.django_db
def test_notification_task_handles_missing_maintenance_request():
    result = send_notifications_for_maintenance_request.run(999999)

    assert result == {
        "success": False,
        "reason": "maintenance_request_not_found",
    }


@pytest.mark.django_db
def test_notification_task_sends_all_pending_notifications(
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

    assert NotificationLog.objects.filter(status=NotificationLog.Status.SENT).count() == 3
    assert NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.EMAIL,
        recipient=building.manager_email,
        status=NotificationLog.Status.SENT,
    ).exists()
    assert NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=building.manager_phone,
        status=NotificationLog.Status.SENT,
    ).exists()
    assert NotificationLog.objects.filter(
        notification_type=NotificationLog.NotificationType.SMS,
        recipient=voice_payload["follow_up_phone"],
        status=NotificationLog.Status.SENT,
    ).exists()


@pytest.mark.django_db
def test_notification_task_is_not_queued_when_transaction_rolls_back(
    building,
    django_capture_on_commit_callbacks,
    mock_send_notifications_task_delay,
    voice_payload,
):
    with pytest.raises(RuntimeError):
        with django_capture_on_commit_callbacks(execute=True):
            with transaction.atomic():
                create_maintenance_request_from_voice_payload(
                    voice_payload,
                    voice_payload,
                )
                raise RuntimeError("Rollback request creation")

    assert MaintenanceRequest.objects.count() == 0
    assert NotificationLog.objects.count() == 0
    assert mock_send_notifications_task_delay == []


@pytest.mark.django_db
def test_notification_enqueue_failure_keeps_api_success_and_pending_logs(
    api_client,
    django_capture_on_commit_callbacks,
    monkeypatch,
    voice_payload,
):
    def raise_enqueue_error(maintenance_request_id):
        raise RuntimeError("Redis unavailable")

    monkeypatch.setattr(
        send_notifications_for_maintenance_request,
        "delay",
        raise_enqueue_error,
    )
    logged_messages = []
    monkeypatch.setattr(
        "apps.maintenance.services.logger.exception",
        lambda message, *args: logged_messages.append(message),
    )

    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(
            "/api/voice/maintenance-requests/",
            voice_payload,
            format="json",
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert MaintenanceRequest.objects.count() == 1
    assert NotificationLog.objects.count() == 3
    assert NotificationLog.objects.filter(
        status=NotificationLog.Status.PENDING,
    ).count() == 3
    assert logged_messages == [
        "notification_task_enqueue_failed maintenance_request_id=%s"
    ]
