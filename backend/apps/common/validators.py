import re

from django.core.exceptions import ValidationError


E164_PHONE_NUMBER_PATTERN = re.compile(r"^\+[0-9]{8,15}$")
E164_PHONE_NUMBER_ERROR = (
    "Enter a valid E.164 phone number with + followed by 8 to 15 digits."
)


def is_e164_phone_number(value):
    return isinstance(value, str) and bool(E164_PHONE_NUMBER_PATTERN.fullmatch(value))


def validate_e164_phone_number(value):
    if not is_e164_phone_number(value):
        raise ValidationError(E164_PHONE_NUMBER_ERROR, code="invalid_phone_number")
