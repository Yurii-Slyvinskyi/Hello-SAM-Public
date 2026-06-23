import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


POSTMARK_EMAIL_URL = "https://api.postmarkapp.com/email"
logger = logging.getLogger(__name__)


class PostmarkError(Exception):
    pass


@dataclass(frozen=True)
class PostmarkEmailResult:
    message_id: str = ""


class PostmarkEmailProvider:
    def send(self, *, to_email, subject, text_body):
        return send_email(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
        )


def send_email(to_email, subject, text_body):
    server_token = os.environ.get("POSTMARK_SERVER_TOKEN")
    sender_email = os.environ.get("POSTMARK_SENDER_EMAIL")
    message_stream = os.environ.get("POSTMARK_MESSAGE_STREAM", "outbound")

    if not server_token:
        logger.error("postmark_provider_missing_server_token")
        raise PostmarkError("POSTMARK_SERVER_TOKEN is required.")

    if not sender_email:
        logger.error("postmark_provider_missing_sender_email")
        raise PostmarkError("POSTMARK_SENDER_EMAIL is required.")

    payload = {
        "From": sender_email,
        "To": to_email,
        "Subject": subject,
        "TextBody": text_body,
        "MessageStream": message_stream,
    }
    request = urllib.request.Request(
        POSTMARK_EMAIL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Postmark-Server-Token": server_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_data = json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        logger.warning(
            "postmark_provider_http_error status_code=%s",
            exc.code,
        )
        raise PostmarkError(f"Postmark API error {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        logger.warning(
            "postmark_provider_connection_error reason=%s",
            exc.reason,
        )
        raise PostmarkError(f"Postmark connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        logger.warning("postmark_provider_timeout")
        raise PostmarkError("Postmark request timed out.") from exc

    return PostmarkEmailResult(message_id=response_data.get("MessageID", ""))
