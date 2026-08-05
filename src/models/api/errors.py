"""Stable API error contract."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: Any = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


class DomainError(Exception):
    """Expected business or authorization failure."""

    def __init__(self, code: str, message: str, status_code: int = 400, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
AUTH_SERVICE_UNAVAILABLE = "AUTH_SERVICE_UNAVAILABLE"
AUTH_PROFILE_INVALID = "AUTH_PROFILE_INVALID"
USER_INACTIVE = "USER_INACTIVE"
FORBIDDEN = "FORBIDDEN"
ROLE_FORBIDDEN = "ROLE_FORBIDDEN"
NO_ACTIVE_UNIT = "NO_ACTIVE_UNIT"
UNIT_SELECTION_REQUIRED = "UNIT_SELECTION_REQUIRED"
UNIT_NOT_FOUND = "UNIT_NOT_FOUND"
TICKET_NOT_FOUND = "TICKET_NOT_FOUND"
ATTACHMENT_NOT_FOUND = "ATTACHMENT_NOT_FOUND"
INVALID_ATTACHMENT = "INVALID_ATTACHMENT"
STORAGE_NOT_CONFIGURED = "STORAGE_NOT_CONFIGURED"
DATABASE_NOT_CONFIGURED = "DATABASE_NOT_CONFIGURED"
INTERNAL_ERROR = "INTERNAL_ERROR"
