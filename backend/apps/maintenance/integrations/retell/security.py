import hashlib
import hmac
import re
import time


RETELL_SIGNATURE_PATTERN = re.compile(r"^v=(\d+),d=([a-fA-F0-9]+)$")
RETELL_SIGNATURE_TOLERANCE_MS = 5 * 60 * 1000


def verify_retell_signature(raw_body, api_key, signature, now_ms=None):
    if not raw_body or not api_key or not signature:
        return False

    match = RETELL_SIGNATURE_PATTERN.match(signature)
    if not match:
        return False

    timestamp = match.group(1)
    received_digest = match.group(2)
    current_time_ms = now_ms if now_ms is not None else int(time.time() * 1000)

    if abs(current_time_ms - int(timestamp)) > RETELL_SIGNATURE_TOLERANCE_MS:
        return False

    raw_body_text = raw_body.decode("utf-8") if isinstance(raw_body, bytes) else raw_body
    message = f"{raw_body_text}{timestamp}".encode("utf-8")
    expected_digest = hmac.new(
        api_key.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_digest, received_digest)
