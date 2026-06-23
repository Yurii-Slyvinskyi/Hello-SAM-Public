from rest_framework import serializers

from apps.common.validators import (
    E164_PHONE_NUMBER_ERROR,
    is_e164_phone_number,
    validate_e164_phone_number,
)
from apps.maintenance.choices import IssueType, Priority


INVALID_FOLLOW_UP_PHONE_VALUES = {
    "caller_phone",
    "user_number",
    "unknown",
    "none",
}


class VoiceMaintenanceRequestSerializer(serializers.Serializer):
    call_id = serializers.CharField(max_length=255)
    called_number = serializers.CharField(
        max_length=32,
        trim_whitespace=False,
        validators=[validate_e164_phone_number],
    )
    caller_phone = serializers.CharField(
        max_length=32,
        trim_whitespace=False,
        validators=[validate_e164_phone_number],
    )
    full_name = serializers.CharField(max_length=255, allow_blank=False)
    unit_number = serializers.CharField(max_length=64)
    use_caller_phone_for_follow_up = serializers.BooleanField()
    follow_up_phone = serializers.CharField(
        max_length=32,
        allow_blank=True,
        trim_whitespace=False,
    )
    issue_type = serializers.ChoiceField(choices=IssueType.choices)
    resident_reported_issue = serializers.CharField()
    description = serializers.CharField()
    location_inside_unit = serializers.CharField(max_length=255)
    ai_priority = serializers.ChoiceField(choices=Priority.choices)
    transcript = serializers.CharField()

    def validate(self, attrs):
        if attrs["use_caller_phone_for_follow_up"]:
            attrs["follow_up_phone"] = attrs["caller_phone"]
            return attrs

        follow_up_phone = attrs["follow_up_phone"]
        if (
            not follow_up_phone
            or follow_up_phone.lower() in INVALID_FOLLOW_UP_PHONE_VALUES
            or not is_e164_phone_number(follow_up_phone)
        ):
            raise serializers.ValidationError(
                {
                    "follow_up_phone": E164_PHONE_NUMBER_ERROR,
                }
            )

        attrs["follow_up_phone"] = follow_up_phone
        return attrs
