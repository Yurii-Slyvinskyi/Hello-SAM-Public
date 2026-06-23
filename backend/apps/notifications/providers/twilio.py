import logging
import os
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class TwilioError(Exception):
    pass


@dataclass(frozen=True)
class TwilioSmsResult:
    message_id: str = ""


class TwilioSmsProvider:
    def send(self, *, to_phone, body):
        return send_sms(to_phone=to_phone, body=body)


def send_sms(to_phone, body):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_phone = os.environ.get("TWILIO_FROM_PHONE")
    messaging_service_sid = os.environ.get("TWILIO_MESSAGING_SERVICE_SID")

    if not account_sid:
        logger.error("twilio_provider_missing_account_sid")
        raise TwilioError("TWILIO_ACCOUNT_SID is required.")

    if not auth_token:
        logger.error("twilio_provider_missing_auth_token")
        raise TwilioError("TWILIO_AUTH_TOKEN is required.")

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        if messaging_service_sid:
            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                to=to_phone,
                body=body,
            )
        else:
            if not from_phone:
                logger.error("twilio_provider_missing_from_phone")
                raise TwilioError(
                    "TWILIO_FROM_PHONE is required when "
                    "TWILIO_MESSAGING_SERVICE_SID is not configured."
                )
            message = client.messages.create(
                from_=from_phone,
                to=to_phone,
                body=body,
            )
    except TwilioError:
        raise
    except Exception as exc:
        logger.warning(
            "twilio_provider_error error_type=%s",
            exc.__class__.__name__,
        )
        raise TwilioError(str(exc)) from exc

    return TwilioSmsResult(message_id=getattr(message, "sid", ""))
