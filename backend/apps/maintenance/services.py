import logging
from dataclasses import dataclass

from django.db import transaction
from rest_framework import serializers

from apps.buildings.models import Building
from apps.calls.models import CallLog
from apps.notifications.services import NotificationOrchestrator
from apps.notifications.tasks import send_notifications_for_maintenance_request

from .choices import Priority
from .models import MaintenanceRequest
from .priority import detect_backend_priority, get_highest_priority


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MaintenanceRequestResult:
    maintenance_request: MaintenanceRequest
    message_for_resident: str


def create_maintenance_request_from_voice_payload(payload, raw_payload):
    notification_orchestrator = NotificationOrchestrator()
    existing_request = MaintenanceRequest.objects.filter(
        call_id=payload["call_id"]
    ).first()
    if existing_request:
        logger.info(
            "duplicate_maintenance_request_call_id call_id=%s maintenance_request_id=%s",
            payload["call_id"],
            existing_request.id,
        )
        _upsert_call_log(existing_request.building, payload, raw_payload)
        return MaintenanceRequestResult(
            maintenance_request=existing_request,
            message_for_resident=_build_resident_message(
                existing_request.final_priority
            ),
        )

    building = _get_active_building(payload["called_number"])
    ai_priority = payload["ai_priority"]
    backend_detection = detect_backend_priority(payload)
    final_priority = get_highest_priority(ai_priority, backend_detection.priority)

    with transaction.atomic():
        maintenance_request, _created = MaintenanceRequest.objects.get_or_create(
            call_id=payload["call_id"],
            defaults={
                "building": building,
                "caller_phone": payload["caller_phone"],
                "full_name": payload["full_name"],
                "follow_up_phone": payload.get("follow_up_phone", ""),
                "use_caller_phone_for_follow_up": payload[
                    "use_caller_phone_for_follow_up"
                ],
                "unit_number": payload["unit_number"],
                "issue_type": payload["issue_type"],
                "resident_reported_issue": payload["resident_reported_issue"],
                "description": payload["description"],
                "location_inside_unit": payload["location_inside_unit"],
                "ai_priority": ai_priority,
                "backend_priority": backend_detection.priority,
                "final_priority": final_priority,
                "is_emergency": final_priority == Priority.EMERGENCY,
                "emergency_reason": backend_detection.reason,
                "transcript": payload["transcript"],
            },
        )

        _upsert_call_log(maintenance_request.building, payload, raw_payload)
        if _created:
            notification_orchestrator.create_pending_logs(maintenance_request)
            _schedule_notification_task_after_commit(maintenance_request.id)

    return MaintenanceRequestResult(
        maintenance_request=maintenance_request,
        message_for_resident=_build_resident_message(
            maintenance_request.final_priority
        ),
    )


def _get_active_building(called_number):
    try:
        building = Building.objects.get(maintenance_phone_number=called_number)
    except Building.DoesNotExist as exc:
        logger.warning(
            "building_lookup_failed called_number=%s",
            called_number,
        )
        raise serializers.ValidationError(
            {"called_number": "No building found for this called_number."}
        ) from exc

    if not building.is_active:
        logger.warning(
            "inactive_building_called building_id=%s called_number=%s",
            building.id,
            called_number,
        )
        raise serializers.ValidationError(
            {"called_number": "Building is inactive for this called_number."}
        )

    return building


def _upsert_call_log(building, payload, raw_payload):
    CallLog.objects.update_or_create(
        call_id=payload["call_id"],
        defaults={
            "building": building,
            "called_number": payload["called_number"],
            "caller_phone": payload["caller_phone"],
            "transcript": payload["transcript"],
            "raw_payload": dict(raw_payload),
        },
    )


def _schedule_notification_task_after_commit(maintenance_request_id):
    def enqueue_notification_task():
        try:
            send_notifications_for_maintenance_request.delay(maintenance_request_id)
        except Exception:
            logger.exception(
                "notification_task_enqueue_failed maintenance_request_id=%s",
                maintenance_request_id,
            )

    transaction.on_commit(enqueue_notification_task)


def _build_resident_message(priority):
    if priority == Priority.NORMAL:
        return "Your maintenance request has been submitted. The team has been notified."

    return (
        f"Your {priority} maintenance request has been submitted. "
        "The team has been notified."
    )
