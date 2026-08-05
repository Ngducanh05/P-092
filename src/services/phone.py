"""Phone-number normalization helpers."""

from __future__ import annotations

import re

from src.models.api.errors import AUTH_PROFILE_INVALID, DomainError

E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


def normalize_e164_phone(phone_number: str | None) -> str | None:
    """Return a strict E.164 phone number or raise a stable auth error."""
    if phone_number is None:
        return None
    if not E164_RE.fullmatch(phone_number):
        raise DomainError(AUTH_PROFILE_INVALID, "Authenticated phone is not normalized E.164.", 401)
    return phone_number
