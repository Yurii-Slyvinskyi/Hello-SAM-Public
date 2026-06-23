import pytest
from rest_framework.test import APIClient

from apps.buildings.models import Building
from apps.companies.models import Company
from apps.maintenance.choices import IssueType, Priority


@pytest.fixture
def api_client():
    client = APIClient()
    client.credentials(HTTP_X_VOICE_AGENT_TOKEN="test-token")
    return client


@pytest.fixture
def unauthenticated_api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def voice_agent_token_settings(settings):
    settings.VOICE_AGENT_TOKEN = "test-token"


@pytest.fixture(autouse=True)
def mock_postmark_send_email(monkeypatch):
    from apps.notifications.providers import postmark

    def send_email(to_email, subject, text_body):
        return postmark.PostmarkEmailResult(message_id="test-postmark-message-id")

    monkeypatch.setattr(postmark, "send_email", send_email)


@pytest.fixture(autouse=True)
def mock_twilio_send_sms(monkeypatch):
    from apps.notifications.providers import twilio

    def send_sms(to_phone, body):
        return twilio.TwilioSmsResult(message_id="test-twilio-message-id")

    monkeypatch.setattr(twilio, "send_sms", send_sms)


@pytest.fixture(autouse=True)
def mock_send_notifications_task_delay(monkeypatch):
    from apps.notifications.tasks import send_notifications_for_maintenance_request

    queued_task_ids = []

    def delay(maintenance_request_id):
        queued_task_ids.append(maintenance_request_id)

    monkeypatch.setattr(send_notifications_for_maintenance_request, "delay", delay)
    return queued_task_ids


@pytest.fixture
def company():
    return Company.objects.create(name="Acme Property Management")


@pytest.fixture
def building(company):
    return Building.objects.create(
        company=company,
        name="Henday Suites",
        address="100 Main Street",
        maintenance_phone_number="+17801111001",
        office_phone_number="+17801111002",
        manager_email="manager@example.com",
        manager_phone="+17801111003",
        is_active=True,
    )


@pytest.fixture
def voice_payload(building):
    return {
        "call_id": "call_123",
        "called_number": building.maintenance_phone_number,
        "caller_phone": "+17802223333",
        "full_name": "Jane Resident",
        "unit_number": "418",
        "use_caller_phone_for_follow_up": True,
        "follow_up_phone": "+17802223333",
        "issue_type": IssueType.PLUMBING,
        "resident_reported_issue": "There is water coming from under my bathroom sink.",
        "description": "Bathroom sink is leaking heavily under the cabinet.",
        "location_inside_unit": "bathroom",
        "ai_priority": Priority.URGENT,
        "transcript": "Full call transcript here.",
    }
