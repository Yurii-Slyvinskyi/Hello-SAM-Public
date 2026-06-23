import logging

from django.conf import settings
from django.utils.crypto import constant_time_compare
from rest_framework.permissions import BasePermission

from .integrations.retell.security import verify_retell_signature


logger = logging.getLogger(__name__)


class HasVoiceAgentToken(BasePermission):
    message = "Invalid voice agent token."

    def has_permission(self, request, view):
        expected_token = getattr(settings, "VOICE_AGENT_TOKEN", "")
        provided_token = request.headers.get("X-Voice-Agent-Token", "")

        if not expected_token:
            logger.error(
                "voice_agent_token_not_configured path=%s",
                request.path,
            )
            return False

        if not provided_token:
            logger.warning(
                "voice_agent_token_missing path=%s",
                request.path,
            )
            return False

        is_valid = constant_time_compare(provided_token, expected_token)
        if not is_valid:
            logger.warning(
                "voice_agent_token_invalid path=%s",
                request.path,
            )

        return is_valid


class HasValidRetellSignature(BasePermission):
    message = "Invalid Retell signature."

    def has_permission(self, request, view):
        api_key = getattr(settings, "RETELL_API_KEY", "")
        signature = request.headers.get("X-Retell-Signature", "")

        if not api_key:
            logger.error(
                "retell_api_key_not_configured path=%s",
                request.path,
            )
            return False

        if not signature:
            logger.warning(
                "retell_signature_missing path=%s",
                request.path,
            )
            return False

        is_valid = verify_retell_signature(
            raw_body=request.body,
            api_key=api_key,
            signature=signature,
        )
        if not is_valid:
            logger.warning(
                "retell_signature_invalid path=%s",
                request.path,
            )

        return is_valid
