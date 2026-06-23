import pytest
from rest_framework import status

from apps.buildings.models import Building
from apps.maintenance.choices import IssueType
from apps.maintenance.models import MaintenanceRequest


@pytest.mark.django_db
def test_successful_request_creates_maintenance_request(api_client, voice_payload):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert MaintenanceRequest.objects.count() == 1

    maintenance_request = MaintenanceRequest.objects.get()
    assert maintenance_request.call_id == voice_payload["call_id"]
    assert maintenance_request.full_name == voice_payload["full_name"]
    assert maintenance_request.resident_reported_issue == voice_payload[
        "resident_reported_issue"
    ]
    assert maintenance_request.final_priority == voice_payload["ai_priority"]


@pytest.mark.django_db
def test_request_is_linked_to_correct_building_by_called_number(
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

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    maintenance_request = MaintenanceRequest.objects.get()
    assert maintenance_request.building == building
    assert maintenance_request.building != other_building


@pytest.mark.django_db
def test_unknown_called_number_returns_validation_error(api_client, voice_payload):
    voice_payload["called_number"] = "+17800000000"

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "called_number" in response.data
    assert MaintenanceRequest.objects.count() == 0


@pytest.mark.django_db
def test_inactive_building_returns_validation_error(
    api_client,
    building,
    voice_payload,
):
    building.is_active = False
    building.save(update_fields=["is_active"])

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "called_number" in response.data
    assert MaintenanceRequest.objects.count() == 0


@pytest.mark.django_db
def test_successful_response_contains_expected_fields(api_client, voice_payload):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert set(response.data) == {
        "success",
        "request_id",
        "final_priority",
        "message_for_resident",
    }
    assert response.data["success"] is True
    assert response.data["request_id"] == MaintenanceRequest.objects.get().id
    assert response.data["final_priority"] == voice_payload["ai_priority"]
    assert response.data["message_for_resident"]


@pytest.mark.django_db
def test_missing_full_name_returns_validation_error(api_client, voice_payload):
    voice_payload.pop("full_name")

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "full_name" in response.data
    assert MaintenanceRequest.objects.count() == 0


@pytest.mark.django_db
def test_blank_full_name_returns_validation_error(api_client, voice_payload):
    voice_payload["full_name"] = ""

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "full_name" in response.data
    assert MaintenanceRequest.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "issue_type",
    [
        IssueType.WATER_LEAK,
        IssueType.COMMON_AREA,
    ],
)
def test_new_issue_type_values_are_accepted(api_client, issue_type, voice_payload):
    voice_payload["issue_type"] = issue_type

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert MaintenanceRequest.objects.get().issue_type == issue_type
