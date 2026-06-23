import pytest
from rest_framework import status

from apps.maintenance.choices import IssueType, Priority
from apps.maintenance.models import MaintenanceRequest


def set_issue_text(payload, text, ai_priority=Priority.NORMAL):
    payload["description"] = text
    payload["resident_reported_issue"] = text
    payload["transcript"] = f"Resident reported: {text}"
    payload["ai_priority"] = ai_priority
    payload["issue_type"] = IssueType.APPLIANCE


@pytest.mark.django_db
@pytest.mark.parametrize(
    (
        "issue_text",
        "ai_priority",
        "expected_backend_priority",
        "expected_final_priority",
        "expected_reason_keyword",
    ),
    [
        (
            "The dishwasher is broken.",
            Priority.NORMAL,
            Priority.NORMAL,
            Priority.NORMAL,
            "",
        ),
        (
            "There is a water leak under the sink.",
            Priority.NORMAL,
            Priority.URGENT,
            Priority.URGENT,
            "water leak",
        ),
        (
            "There is no heat in the unit.",
            Priority.NORMAL,
            Priority.URGENT,
            Priority.URGENT,
            "no heat",
        ),
        (
            "There is a gas smell near the stove.",
            Priority.NORMAL,
            Priority.EMERGENCY,
            Priority.EMERGENCY,
            "gas smell",
        ),
        (
            "There is smoke and fire in the hallway.",
            Priority.NORMAL,
            Priority.EMERGENCY,
            Priority.EMERGENCY,
            "fire",
        ),
        (
            "The fridge is making a loud noise.",
            Priority.URGENT,
            Priority.NORMAL,
            Priority.URGENT,
            "",
        ),
        (
            "There is a gas smell in the apartment.",
            Priority.URGENT,
            Priority.EMERGENCY,
            Priority.EMERGENCY,
            "gas smell",
        ),
    ],
)
def test_backend_priority_detection(
    api_client,
    voice_payload,
    issue_text,
    ai_priority,
    expected_backend_priority,
    expected_final_priority,
    expected_reason_keyword,
):
    set_issue_text(voice_payload, issue_text, ai_priority)

    response = api_client.post(
        "/api/voice/maintenance-requests/",
        voice_payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["final_priority"] == expected_final_priority

    maintenance_request = MaintenanceRequest.objects.get()
    assert maintenance_request.ai_priority == ai_priority
    assert maintenance_request.backend_priority == expected_backend_priority
    assert maintenance_request.final_priority == expected_final_priority
    assert maintenance_request.is_emergency is (
        expected_final_priority == Priority.EMERGENCY
    )

    if expected_reason_keyword:
        assert expected_reason_keyword in maintenance_request.emergency_reason.lower()
    else:
        assert maintenance_request.emergency_reason == ""
