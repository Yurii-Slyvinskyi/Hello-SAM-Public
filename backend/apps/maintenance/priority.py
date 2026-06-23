from dataclasses import dataclass

from .choices import Priority


EMERGENCY_KEYWORDS = (
    "fire",
    "smoke",
    "gas smell",
    "carbon monoxide",
    "flooding",
    "electrical sparks",
    "sparks",
    "break-in",
    "break in",
    "serious safety issue",
)

URGENT_KEYWORDS = (
    "active water leak",
    "water leak",
    "leaking heavily",
    "no heat",
    "no power",
    "toilet overflowing",
    "sewage backup",
    "broken exterior lock",
)

PRIORITY_RANK = {
    Priority.NORMAL: 0,
    Priority.URGENT: 1,
    Priority.EMERGENCY: 2,
}


@dataclass(frozen=True)
class PriorityDetection:
    priority: str
    reason: str


def detect_backend_priority(payload):
    text = " ".join(
        [
            payload.get("description", ""),
            payload.get("resident_reported_issue", ""),
            payload.get("transcript", ""),
        ]
    ).lower()

    emergency_keyword = _find_keyword(text, EMERGENCY_KEYWORDS)
    if emergency_keyword:
        return PriorityDetection(
            priority=Priority.EMERGENCY,
            reason=f"Detected emergency keyword: {emergency_keyword}",
        )

    urgent_keyword = _find_keyword(text, URGENT_KEYWORDS)
    if urgent_keyword:
        return PriorityDetection(
            priority=Priority.URGENT,
            reason=f"Detected urgent keyword: {urgent_keyword}",
        )

    return PriorityDetection(
        priority=Priority.NORMAL,
        reason="",
    )


def get_highest_priority(first_priority, second_priority):
    if PRIORITY_RANK[first_priority] >= PRIORITY_RANK[second_priority]:
        return first_priority

    return second_priority


def _find_keyword(text, keywords):
    return next((keyword for keyword in keywords if keyword in text), "")
