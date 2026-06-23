import pytest
from django.core.exceptions import ValidationError
from rest_framework import status

from apps.buildings.models import Building
from apps.calls.models import CallLog
from apps.maintenance.models import MaintenanceRequest
from apps.notifications.models import NotificationLog


@pytest.mark.django_db
def test_valid_e164_building_phone_numbers_are_accepted(company):
    building = Building(
        company=company,
        name="Valid Phones",
        address="100 Main Street",
        maintenance_phone_number="+13659904115",
        office_phone_number="+17801111002",
        manager_email="manager@example.com",
        manager_phone="+17802223333",
        is_active=True,
    )

    building.full_clean()


@pytest.mark.django_db
def test_invalid_maintenance_phone_number_is_rejected(company):
    building = Building(
        company=company,
        name="Invalid Maintenance Phone",
        address="100 Main Street",
        maintenance_phone_number="+1",
        office_phone_number="+17801111002",
        manager_email="manager@example.com",
        manager_phone="+17802223333",
        is_active=True,
    )

    with pytest.raises(ValidationError) as exc_info:
        building.full_clean()

    assert "maintenance_phone_number" in exc_info.value.message_dict


@pytest.mark.django_db
def test_invalid_office_phone_number_is_rejected(company):
    building = Building(
        company=company,
        name="Invalid Office Phone",
        address="100 Main Street",
        maintenance_phone_number="+13659904115",
        office_phone_number="7802223333",
        manager_email="manager@example.com",
        manager_phone="+17802223333",
        is_active=True,
    )

    with pytest.raises(ValidationError) as exc_info:
        building.full_clean()

    assert "office_phone_number" in exc_info.value.message_dict


@pytest.mark.django_db
def test_invalid_manager_phone_is_rejected(company):
    building = Building(
        company=company,
        name="Invalid Manager Phone",
        address="100 Main Street",
        maintenance_phone_number="+13659904115",
        office_phone_number="+17801111002",
        manager_email="manager@example.com",
        manager_phone="caller_phone",
        is_active=True,
    )

    with pytest.raises(ValidationError) as exc_info:
        building.full_clean()

    assert "manager_phone" in exc_info.value.message_dict


@pytest.mark.django_db
def test_valid_voice_request_with_valid_phone_numbers_succeeds(
    api_client,
    voice_payload,
):
    voice_payload["caller_phone"] = "+17802223333"
    voice_payload["follow_up_phone"] = "+17802223333"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_invalid_called_number_is_rejected(api_client, voice_payload):
    voice_payload["called_number"] = "+1"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "called_number" in response.data
    assert MaintenanceRequest.objects.count() == 0
    assert CallLog.objects.count() == 0
    assert NotificationLog.objects.count() == 0


@pytest.mark.django_db
def test_invalid_caller_phone_is_rejected(api_client, voice_payload):
    voice_payload["caller_phone"] = "user_number"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "caller_phone" in response.data
    assert MaintenanceRequest.objects.count() == 0
    assert NotificationLog.objects.count() == 0


@pytest.mark.django_db
def test_invalid_alternate_follow_up_phone_is_rejected(api_client, voice_payload):
    voice_payload["use_caller_phone_for_follow_up"] = False
    voice_payload["follow_up_phone"] = "780-222-3333"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "follow_up_phone" in response.data
    assert MaintenanceRequest.objects.count() == 0
    assert NotificationLog.objects.count() == 0
