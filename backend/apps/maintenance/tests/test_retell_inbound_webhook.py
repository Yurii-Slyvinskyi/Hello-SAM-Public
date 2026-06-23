import hashlib
import hmac
import json
import time

import pytest
from rest_framework import status

from apps.buildings.models import Building
from apps.calls.models import CallLog
from apps.maintenance.models import MaintenanceRequest
from apps.notifications.models import NotificationLog


RETELL_INBOUND_URL = "/api/voice/retell/inbound-call/"
RETELL_API_KEY = "test-retell-api-key"


def sign_retell_body(raw_body, api_key=RETELL_API_KEY, timestamp=None):
    timestamp = str(timestamp or int(time.time() * 1000))
    digest = hmac.new(
        api_key.encode("utf-8"),
        f"{raw_body}{timestamp}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"v={timestamp},d={digest}"


def retell_inbound_payload(to_number):
    return {
        "event": "call_inbound",
        "call_inbound": {
            "agent_id": "agent_12345",
            "agent_version": 1,
            "from_number": "+17802223333",
            "to_number": to_number,
        },
    }


def post_signed_retell_payload(client, settings, payload, raw_body=None):
    settings.RETELL_API_KEY = RETELL_API_KEY
    raw_body = raw_body or json.dumps(payload, separators=(",", ":"))
    return client.post(
        RETELL_INBOUND_URL,
        data=raw_body,
        content_type="application/json",
        HTTP_X_RETELL_SIGNATURE=sign_retell_body(raw_body),
    )


@pytest.mark.django_db
def test_missing_retell_signature_returns_403(
    settings,
    unauthenticated_api_client,
    building,
):
    settings.RETELL_API_KEY = RETELL_API_KEY

    response = unauthenticated_api_client.post(
        RETELL_INBOUND_URL,
        retell_inbound_payload(building.maintenance_phone_number),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_invalid_retell_signature_returns_403(
    settings,
    unauthenticated_api_client,
    building,
):
    settings.RETELL_API_KEY = RETELL_API_KEY
    raw_body = json.dumps(
        retell_inbound_payload(building.maintenance_phone_number),
        separators=(",", ":"),
    )

    response = unauthenticated_api_client.post(
        RETELL_INBOUND_URL,
        data=raw_body,
        content_type="application/json",
        HTTP_X_RETELL_SIGNATURE=f"v={int(time.time() * 1000)},d=bad",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_stale_retell_signature_timestamp_returns_403(
    settings,
    unauthenticated_api_client,
    building,
):
    settings.RETELL_API_KEY = RETELL_API_KEY
    raw_body = json.dumps(
        retell_inbound_payload(building.maintenance_phone_number),
        separators=(",", ":"),
    )
    stale_timestamp = int(time.time() * 1000) - (6 * 60 * 1000)

    response = unauthenticated_api_client.post(
        RETELL_INBOUND_URL,
        data=raw_body,
        content_type="application/json",
        HTTP_X_RETELL_SIGNATURE=sign_retell_body(
            raw_body,
            timestamp=stale_timestamp,
        ),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_missing_retell_api_key_denies_request(
    settings,
    unauthenticated_api_client,
    building,
):
    settings.RETELL_API_KEY = ""
    payload = retell_inbound_payload(building.maintenance_phone_number)
    raw_body = json.dumps(payload, separators=(",", ":"))

    response = unauthenticated_api_client.post(
        RETELL_INBOUND_URL,
        data=raw_body,
        content_type="application/json",
        HTTP_X_RETELL_SIGNATURE=sign_retell_body(raw_body),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_valid_retell_inbound_payload_returns_building_dynamic_variables(
    settings,
    unauthenticated_api_client,
    building,
):
    response = post_signed_retell_payload(
        unauthenticated_api_client,
        settings,
        retell_inbound_payload(building.maintenance_phone_number),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["call_inbound"]["dynamic_variables"] == {
        "office_phone_number": building.office_phone_number,
        "building_name": building.name,
    }
    assert response.data["call_inbound"]["metadata"] == {
        "building_id": str(building.id),
    }


@pytest.mark.django_db
def test_retell_inbound_to_number_maps_to_correct_building(
    settings,
    unauthenticated_api_client,
    company,
    building,
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

    response = post_signed_retell_payload(
        unauthenticated_api_client,
        settings,
        retell_inbound_payload(other_building.maintenance_phone_number),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["call_inbound"]["dynamic_variables"][
        "office_phone_number"
    ] == other_building.office_phone_number
    assert response.data["call_inbound"]["dynamic_variables"]["building_name"] == (
        other_building.name
    )
    assert response.data["call_inbound"]["metadata"]["building_id"] == str(
        other_building.id
    )
    assert response.data["call_inbound"]["metadata"]["building_id"] != str(
        building.id
    )


@pytest.mark.django_db
def test_unknown_retell_to_number_returns_safe_fallback_without_creating_records(
    settings,
    unauthenticated_api_client,
):
    response = post_signed_retell_payload(
        unauthenticated_api_client,
        settings,
        retell_inbound_payload("+17800000000"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "call_inbound": {
            "dynamic_variables": {},
            "metadata": {},
        }
    }
    assert MaintenanceRequest.objects.count() == 0
    assert CallLog.objects.count() == 0
    assert NotificationLog.objects.count() == 0


@pytest.mark.django_db
def test_inactive_building_returns_safe_fallback_without_office_phone_number(
    settings,
    unauthenticated_api_client,
    building,
):
    building.is_active = False
    building.save(update_fields=["is_active"])

    response = post_signed_retell_payload(
        unauthenticated_api_client,
        settings,
        retell_inbound_payload(building.maintenance_phone_number),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["call_inbound"]["dynamic_variables"] == {}
    assert "office_phone_number" not in response.data["call_inbound"][
        "dynamic_variables"
    ]
    assert MaintenanceRequest.objects.count() == 0
    assert CallLog.objects.count() == 0
    assert NotificationLog.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"call_inbound": {"from_number": "+17802223333", "to_number": "+17801111001"}},
        {
            "event": "call_started",
            "call_inbound": {
                "from_number": "+17802223333",
                "to_number": "+17801111001",
            },
        },
    ],
)
def test_missing_or_wrong_retell_event_returns_validation_error(
    settings,
    unauthenticated_api_client,
    payload,
):
    response = post_signed_retell_payload(
        unauthenticated_api_client,
        settings,
        payload,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "event" in response.data


@pytest.mark.django_db
def test_missing_retell_to_number_returns_validation_error(
    settings,
    unauthenticated_api_client,
):
    payload = {
        "event": "call_inbound",
        "call_inbound": {
            "from_number": "+17802223333",
        },
    }

    response = post_signed_retell_payload(
        unauthenticated_api_client,
        settings,
        payload,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "to_number" in response.data["call_inbound"]


@pytest.mark.django_db
def test_malformed_retell_to_number_returns_validation_error_without_creating_records(
    settings,
    unauthenticated_api_client,
):
    response = post_signed_retell_payload(
        unauthenticated_api_client,
        settings,
        retell_inbound_payload("+1"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "to_number" in response.data["call_inbound"]
    assert MaintenanceRequest.objects.count() == 0
    assert CallLog.objects.count() == 0
    assert NotificationLog.objects.count() == 0


@pytest.mark.django_db
def test_retell_signature_verification_uses_exact_raw_request_body(
    settings,
    unauthenticated_api_client,
    building,
):
    payload = retell_inbound_payload(building.maintenance_phone_number)
    raw_body = json.dumps(payload, indent=2)

    response = post_signed_retell_payload(
        unauthenticated_api_client,
        settings,
        payload,
        raw_body=raw_body,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["call_inbound"]["dynamic_variables"][
        "office_phone_number"
    ] == building.office_phone_number


@pytest.mark.django_db
def test_create_maintenance_request_still_uses_voice_agent_token(
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
