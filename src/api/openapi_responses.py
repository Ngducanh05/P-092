"""Reusable OpenAPI response metadata."""

from typing import Any

from src.models.api.errors import (
    ACTOR_FORBIDDEN,
    ATTACHMENT_NOT_FOUND,
    AUTH_SERVICE_UNAVAILABLE,
    AUTH_TOKEN_INVALID,
    FORBIDDEN,
    INTERNAL_ERROR,
    INVALID_ATTACHMENT,
    STORAGE_NOT_CONFIGURED,
    TICKET_NOT_FOUND,
    UNIT_NOT_FOUND,
    ErrorResponse,
)

REQUEST_ID_EXAMPLE = "550e8400-e29b-41d4-a716-446655440000"


def error_response(description: str, code: str, message: str) -> dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": code,
                        "message": message,
                        "details": None,
                        "request_id": REQUEST_ID_EXAMPLE,
                    }
                }
            }
        },
    }


BAD_REQUEST_RESPONSE = error_response(
    "Invalid request or business validation failure.",
    INVALID_ATTACHMENT,
    "Invalid attachment upload session.",
)
UNAUTHORIZED_RESPONSE = error_response(
    "Missing, invalid, or expired Supabase Bearer access token.",
    AUTH_TOKEN_INVALID,
    "Invalid access token.",
)
FORBIDDEN_RESPONSE = error_response(
    "Authenticated actor is inactive or not allowed for this operation.",
    ACTOR_FORBIDDEN,
    "Actor is not allowed for this operation.",
)
GENERIC_FORBIDDEN_RESPONSE = error_response(
    "Authenticated user is forbidden from this resource.",
    FORBIDDEN,
    "Forbidden.",
)
UNIT_NOT_FOUND_RESPONSE = error_response(
    "Unit was not found or is not available to the current resident.",
    UNIT_NOT_FOUND,
    "Unit not found.",
)
TICKET_NOT_FOUND_RESPONSE = error_response(
    "Ticket was not found or is not visible to the current user.",
    TICKET_NOT_FOUND,
    "Ticket not found.",
)
ATTACHMENT_NOT_FOUND_RESPONSE = error_response(
    "Attachment was not found or is not visible to the current user.",
    ATTACHMENT_NOT_FOUND,
    "Attachment not found.",
)
AUTH_SERVICE_UNAVAILABLE_RESPONSE = error_response(
    "Supabase Auth or a required authentication dependency is unavailable.",
    AUTH_SERVICE_UNAVAILABLE,
    "Authentication service is unavailable.",
)
STORAGE_UNAVAILABLE_RESPONSE = error_response(
    "Supabase Storage or a required storage dependency is unavailable.",
    STORAGE_NOT_CONFIGURED,
    "Supabase Storage is not configured.",
)
INTERNAL_SERVER_ERROR_RESPONSE = error_response(
    "Unexpected internal server error.",
    INTERNAL_ERROR,
    "Internal server error.",
)

AUTHENTICATED_RESPONSES = {
    401: UNAUTHORIZED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
    503: AUTH_SERVICE_UNAVAILABLE_RESPONSE,
    500: INTERNAL_SERVER_ERROR_RESPONSE,
}
