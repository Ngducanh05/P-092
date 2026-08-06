"""OpenAPI documentation coverage for implemented T-006 APIs."""

import json

import pytest

from src.config import get_settings
from src.main import app

EXPECTED_OPERATIONS = {
    ("/health", "get"): "health_check",
    ("/ready", "get"): "readiness_check",
    ("/api/v1/auth/me", "get"): "get_current_actor",
    ("/api/v1/units/my", "get"): "list_my_units",
    ("/api/v1/storage/ticket-attachments/upload-url", "post"): "create_ticket_attachment_upload_url",
    ("/api/v1/tickets", "post"): "create_ticket",
    ("/api/v1/tickets/my", "get"): "list_my_tickets",
    ("/api/v1/tickets/{ticket_id}", "get"): "get_ticket",
    (
        "/api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url",
        "get",
    ): "get_ticket_attachment_download_url",
    ("/api/v1/bql/tickets", "get"): "list_bql_tickets",
}

PROTECTED_OPERATIONS = [
    ("/api/v1/auth/me", "get"),
    ("/api/v1/units/my", "get"),
    ("/api/v1/storage/ticket-attachments/upload-url", "post"),
    ("/api/v1/tickets", "post"),
    ("/api/v1/tickets/my", "get"),
    ("/api/v1/tickets/{ticket_id}", "get"),
    ("/api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url", "get"),
    ("/api/v1/bql/tickets", "get"),
]


@pytest.mark.asyncio
async def test_openapi_json_returns_200(client):
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "FixIt Agent API"


def test_expected_t006_api_paths_exist():
    schema = app.openapi()

    for path, _method in EXPECTED_OPERATIONS:
        assert path in schema["paths"]


def test_protected_endpoints_declare_bearer_security():
    schema = app.openapi()

    security_scheme = schema["components"]["securitySchemes"]["SupabaseBearerAuth"]
    assert security_scheme["type"] == "http"
    assert security_scheme["scheme"] == "bearer"
    assert security_scheme["bearerFormat"] == "JWT"

    for path, method in PROTECTED_OPERATIONS:
        operation = schema["paths"][path][method]
        assert operation["security"] == [{"SupabaseBearerAuth": []}]


def test_public_health_and_ready_do_not_require_authentication():
    schema = app.openapi()

    assert not schema["paths"]["/health"]["get"].get("security")
    assert not schema["paths"]["/ready"]["get"].get("security")


def test_common_error_schema_exists():
    schema = app.openapi()

    error_schema = schema["components"]["schemas"]["ErrorResponse"]
    assert "error" in error_schema["properties"]
    assert "ErrorBody" in json.dumps(error_schema)


def test_ticket_creation_has_request_examples():
    schema = app.openapi()
    request_content = schema["paths"]["/api/v1/tickets"]["post"]["requestBody"]["content"]["application/json"]
    ticket_schema = schema["components"]["schemas"]["TicketCreateRequest"]

    assert "examples" in request_content
    assert request_content["examples"]["water_leak"]["value"]["attachment_upload_ids"]
    assert ticket_schema["example"]["title"] == "Rò rỉ nước tại hành lang tầng 10"


def test_important_operations_have_docs_and_stable_operation_ids():
    schema = app.openapi()

    for (path, method), operation_id in EXPECTED_OPERATIONS.items():
        operation = schema["paths"][path][method]
        assert operation["operationId"] == operation_id
        assert operation["summary"]
        assert operation["description"]


def test_openapi_schema_does_not_expose_private_storage_paths_or_secret_values():
    schema_text = json.dumps(app.openapi(), ensure_ascii=False)

    assert "storage_path" not in schema_text
    assert "file_url" not in schema_text
    assert "SUPABASE_SECRET_KEY" not in schema_text
    assert "DATABASE_URL" not in schema_text
    assert "service_role" not in schema_text

    settings = get_settings()
    for value in [
        settings.database_url,
        settings.supabase_url,
        settings.supabase_publishable_key,
        settings.supabase_secret_key,
        settings.openai_api_key,
    ]:
        if value and len(value) > 8:
            assert value not in schema_text


@pytest.mark.asyncio
async def test_docs_and_redoc_remain_enabled(client):
    docs_response = await client.get("/docs")
    redoc_response = await client.get("/redoc")

    assert docs_response.status_code == 200
    assert "text/html" in docs_response.headers["content-type"]
    assert redoc_response.status_code == 200
    assert "text/html" in redoc_response.headers["content-type"]
