from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .integrations.retell.inbound import build_retell_inbound_call_response
from .permissions import HasValidRetellSignature, HasVoiceAgentToken
from .serializers import RetellInboundCallSerializer, VoiceMaintenanceRequestSerializer
from .services import create_maintenance_request_from_voice_payload


class VoiceMaintenanceRequestCreateView(APIView):
    permission_classes = [HasVoiceAgentToken]

    def post(self, request):
        serializer = VoiceMaintenanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = create_maintenance_request_from_voice_payload(
            serializer.validated_data,
            request.data,
        )
        maintenance_request = result.maintenance_request

        return Response(
            {
                "success": True,
                "request_id": maintenance_request.id,
                "final_priority": maintenance_request.final_priority,
                "message_for_resident": result.message_for_resident,
            },
            status=status.HTTP_201_CREATED,
        )


class RetellInboundCallView(APIView):
    permission_classes = [HasValidRetellSignature]

    def post(self, request):
        serializer = RetellInboundCallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            build_retell_inbound_call_response(serializer.validated_data),
            status=status.HTTP_200_OK,
        )
