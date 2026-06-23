import pytest
from rest_framework import status

from apps.buildings.models import Building
from apps.maintenance.models import MaintenanceRequest
from apps.notifications.models import NotificationLog


@pytest.mark.django_db
def test_caller_phone_follow_up_placeholder_is_normalized_to_caller_phone(
    api_client,
    voice_payload,
):
    voice_payload["use_caller_phone_for_follow_up"] = True
    voice_payload["follow_up_phone"] = "caller_phone"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    assert maintenance_request.follow_up_phone == voice_payload["caller_phone"]


@pytest.mark.django_db
def test_resident_sms_uses_real_caller_phone_when_follow_up_placeholder_is_sent(
    api_client,
    voice_payload,
):
    voice_payload["use_caller_phone_for_follow_up"] = True
    voice_payload["follow_up_phone"] = "caller_phone"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    resident_sms_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.SMS,
        purpose=NotificationLog.Purpose.RESIDENT_SMS,
    )
    assert resident_sms_log.recipient == voice_payload["caller_phone"]
    assert resident_sms_log.recipient != "caller_phone"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_follow_up_phone",
    ["caller_phone", "user_number", "unknown", "none", ""],
)
def test_placeholder_follow_up_phone_is_rejected_when_not_using_caller_phone(
    api_client,
    invalid_follow_up_phone,
    voice_payload,
):
    voice_payload["use_caller_phone_for_follow_up"] = False
    voice_payload["follow_up_phone"] = invalid_follow_up_phone

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "follow_up_phone" in response.data
    assert MaintenanceRequest.objects.count() == 0
    assert NotificationLog.objects.count() == 0


@pytest.mark.django_db
def test_real_alternate_follow_up_phone_works_when_not_using_caller_phone(
    api_client,
    voice_payload,
):
    alternate_phone = "+17805550123"
    voice_payload["use_caller_phone_for_follow_up"] = False
    voice_payload["follow_up_phone"] = alternate_phone

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    assert maintenance_request.follow_up_phone == alternate_phone

    resident_sms_log = NotificationLog.objects.get(
        notification_type=NotificationLog.NotificationType.SMS,
        purpose=NotificationLog.Purpose.RESIDENT_SMS,
    )
    assert resident_sms_log.recipient == alternate_phone


@pytest.mark.django_db
def test_retell_called_number_payload_still_maps_to_building(
    api_client,
    company,
    building,
    voice_payload,
):
    other_building = Building.objects.create(
        company=company,
        name="Other Building",
        address="200 Main Street",
        maintenance_phone_number="+17809999999",
        office_phone_number="+17809999998",
        manager_email="other-manager@example.com",
        manager_phone="+17809999997",
        is_active=True,
    )
    voice_payload["call_id"] = "retell_call_123"
    voice_payload["called_number"] = building.maintenance_phone_number

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    maintenance_request = MaintenanceRequest.objects.get()
    assert maintenance_request.building == building
    assert maintenance_request.building != other_building
