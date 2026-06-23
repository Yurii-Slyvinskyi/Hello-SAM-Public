from apps.maintenance.choices import Priority
from apps.notifications.models import NotificationLog


class ManagerEmailMessageBuilder:
    def build_subject(self, maintenance_request):
        priority_prefix = _priority_prefix(maintenance_request.final_priority)

        return (
            f"{priority_prefix}{maintenance_request.building.name} - "
            f"Unit {maintenance_request.unit_number} Maintenance Request"
        )

    def build_body(self, maintenance_request):
        return "\n".join(
            [
                "New maintenance request",
                "",
                f"Building: {maintenance_request.building.name}",
                f"Unit: {maintenance_request.unit_number}",
                f"Resident: {maintenance_request.full_name}",
                f"Priority: {maintenance_request.final_priority}",
                f"Issue type: {maintenance_request.issue_type}",
                "",
                "Resident reported issue:",
                maintenance_request.resident_reported_issue,
                "",
                "Description:",
                maintenance_request.description,
                "",
                "Location:",
                maintenance_request.location_inside_unit.title(),
                "",
                f"Follow-up phone: {maintenance_request.follow_up_phone}",
                f"Caller phone: {maintenance_request.caller_phone}",
            ]
        )


class SmsMessageBuilder:
    def build_body(self, notification_log):
        maintenance_request = notification_log.maintenance_request

        if notification_log.purpose == NotificationLog.Purpose.MANAGER_SMS:
            return self.build_manager_body(maintenance_request)

        if notification_log.purpose == NotificationLog.Purpose.RESIDENT_SMS:
            return self.build_resident_body(maintenance_request)

        if notification_log.recipient == maintenance_request.building.manager_phone:
            return self.build_manager_body(maintenance_request)

        return self.build_resident_body(maintenance_request)

    def build_manager_body(self, maintenance_request):
        follow_up_phone = (
            maintenance_request.follow_up_phone or maintenance_request.caller_phone
        )
        description = maintenance_request.description.strip().rstrip(".")

        return (
            f"{maintenance_request.final_priority.upper()} maintenance at "
            f"{maintenance_request.building.name}, unit "
            f"{maintenance_request.unit_number}, "
            f"{maintenance_request.full_name}. "
            f"{description}. "
            f"Follow-up: {follow_up_phone}"
        )

    def build_resident_body(self, maintenance_request):
        priority_wording = _resident_priority_wording(
            maintenance_request.final_priority
        )

        return (
            f"Your {priority_wording}maintenance request for unit "
            f"{maintenance_request.unit_number} has been submitted. "
            "The team has been notified."
        )


def _priority_prefix(priority):
    if priority in {Priority.URGENT, Priority.EMERGENCY}:
        return f"[{priority.upper()}] "

    return ""


def _resident_priority_wording(priority):
    if priority in {Priority.URGENT, Priority.EMERGENCY}:
        return f"{priority} "

    return ""
