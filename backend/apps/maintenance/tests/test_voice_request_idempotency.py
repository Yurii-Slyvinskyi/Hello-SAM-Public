import pytest
from rest_framework import status

from apps.calls.models import CallLog
from apps.maintenance.models import MaintenanceRequest


@pytest.mark.django_db
def test_duplicate_call_id_returns_existing_request_response(api_client, voice_payload):
    first_response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )
    second_payload = {
        **voice_payload,
        "full_name": "Different Resident",
    }
    second_response = api_client.post(
        "/api/voice/maintenance-requests/",
        second_payload,
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert second_response.data["success"] is True
    assert second_response.data["request_id"] == first_response.data["request_id"]
    assert second_response.data["final_priority"] == first_response.data[
        "final_priority"
    ]
    assert second_response.data["message_for_resident"]
    assert set(second_response.data) == {
        "success",
        "request_id",
        "final_priority",
        "message_for_resident",
    }
    assert MaintenanceRequest.objects.count() == 1
    assert MaintenanceRequest.objects.get().full_name == voice_payload["full_name"]
    assert CallLog.objects.count() == 1


@pytest.mark.django_db
def test_successful_request_creates_call_log(api_client, building, voice_payload):
    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert CallLog.objects.count() == 1

    call_log = CallLog.objects.get()
    assert call_log.building == building
    assert call_log.call_id == voice_payload["call_id"]
    assert call_log.called_number == voice_payload["called_number"]
    assert call_log.caller_phone == voice_payload["caller_phone"]
    assert call_log.transcript == voice_payload["transcript"]


@pytest.mark.django_db
def test_successful_request_updates_existing_call_log(
    api_client,
    building,
    voice_payload,
):
    CallLog.objects.create(
        building=building,
        call_id=voice_payload["call_id"],
        called_number="+10000000000",
        caller_phone="+10000000001",
        transcript="Old transcript.",
        raw_payload={"old": True},
    )

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert CallLog.objects.count() == 1

    call_log = CallLog.objects.get()
    assert call_log.called_number == voice_payload["called_number"]
    assert call_log.caller_phone == voice_payload["caller_phone"]
    assert call_log.transcript == voice_payload["transcript"]
    assert call_log.raw_payload["call_id"] == voice_payload["call_id"]
