from rest_framework import serializers

from apps.common.validators import validate_e164_phone_number


class RetellCallInboundSerializer(serializers.Serializer):
    agent_id = serializers.CharField(required=False, allow_blank=True)
    agent_version = serializers.IntegerField(required=False)
    from_number = serializers.CharField(required=False, allow_blank=True)
    to_number = serializers.CharField(
        max_length=32,
        trim_whitespace=False,
        validators=[validate_e164_phone_number],
    )


class RetellInboundCallSerializer(serializers.Serializer):
    event = serializers.ChoiceField(choices=["call_inbound"])
    call_inbound = RetellCallInboundSerializer()
