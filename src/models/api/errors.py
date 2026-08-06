"""Stable API error contract."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ERROR_RESPONSE_EXAMPLE = {
    "error": {
        "code": "AUTH_TOKEN_INVALID",
        "message": "Invalid access token.",
        "details": None,
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
    }
}


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": ERROR_RESPONSE_EXAMPLE["error"]})

    code: str = Field(description="Stable machine-readable error code.", examples=["AUTH_TOKEN_INVALID"])
    message: str = Field(description="Safe human-readable error message.", examples=["Invalid access token."])
    details: Any = Field(default=None, description="Optional structured details. Null when no safe details are available.")
    request_id: str | None = Field(
        default=None,
        description="Request correlation ID returned in the x-request-id response header.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": ERROR_RESPONSE_EXAMPLE})

    error: ErrorBody = Field(description="Stable error envelope used by API domain and authorization failures.")


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
AUTH_PROFILE_CONFLICT = "AUTH_PROFILE_CONFLICT"
USER_INACTIVE = "USER_INACTIVE"
FORBIDDEN = "FORBIDDEN"
ROLE_FORBIDDEN = "ROLE_FORBIDDEN"
ACTOR_FORBIDDEN = "ACTOR_FORBIDDEN"
NO_ACTIVE_UNIT = "NO_ACTIVE_UNIT"
UNIT_SELECTION_REQUIRED = "UNIT_SELECTION_REQUIRED"
UNIT_NOT_FOUND = "UNIT_NOT_FOUND"
TICKET_NOT_FOUND = "TICKET_NOT_FOUND"
ATTACHMENT_NOT_FOUND = "ATTACHMENT_NOT_FOUND"
INVALID_ATTACHMENT = "INVALID_ATTACHMENT"
STORAGE_NOT_CONFIGURED = "STORAGE_NOT_CONFIGURED"
DATABASE_NOT_CONFIGURED = "DATABASE_NOT_CONFIGURED"
INTERNAL_ERROR = "INTERNAL_ERROR"
