import logging

from apps.buildings.models import Building


logger = logging.getLogger(__name__)


def build_retell_inbound_call_response(payload):
    to_number = payload["call_inbound"]["to_number"]
    building = Building.objects.filter(maintenance_phone_number=to_number).first()

    if not building:
        logger.warning("retell_inbound_building_not_found to_number=%s", to_number)
        return _fallback_response()

    if not building.is_active:
        logger.warning(
            "retell_inbound_building_inactive building_id=%s to_number=%s",
            building.id,
            to_number,
        )
        return _fallback_response()

    return {
        "call_inbound": {
            "dynamic_variables": {
                "office_phone_number": str(building.office_phone_number),
                "building_name": str(building.name),
            },
            "metadata": {
                "building_id": str(building.id),
            },
        }
    }


def _fallback_response():
    return {
        "call_inbound": {
            "dynamic_variables": {},
            "metadata": {},
        }
    }
