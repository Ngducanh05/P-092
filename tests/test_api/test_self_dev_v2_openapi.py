from src.main import app

REQUIRED_PATHS = {
    "/api/v1/auth/otp/request",
    "/api/v1/auth/otp/verify",
    "/api/v1/me",
    "/api/v1/me/bind-unit",
    "/api/v1/catalog/locations",
    "/api/v1/catalog/categories",
    "/api/v1/tickets",
    "/api/v1/tickets/{ticket_id}",
    "/api/v1/tickets/{ticket_id}/cancel",
    "/api/v1/tickets/{ticket_id}/supplements",
    "/api/v1/notifications",
    "/api/v1/notifications/{notification_id}/read",
    "/api/v1/coordinator/tickets",
    "/api/v1/coordinator/tickets/{ticket_id}",
    "/api/v1/coordinator/tickets/{ticket_id}/manual-review/resolve",
    "/api/v1/coordinator/tickets/{ticket_id}/request-information",
    "/api/v1/coordinator/tickets/{ticket_id}/approve",
    "/api/v1/coordinator/tickets/{ticket_id}/classification",
    "/api/v1/coordinator/tickets/{ticket_id}/start",
    "/api/v1/coordinator/tickets/{ticket_id}/complete",
    "/api/v1/coordinator/tickets/{ticket_id}/unresolvable",
    "/api/v1/coordinator/audit-logs",
    "/api/v1/coordinator/reports/tickets-summary",
    "/api/v1/coordinator/reports/sla-performance",
    "/api/v1/coordinator/reports/export",
}


def test_openapi_contains_self_dev_v2_paths_and_no_technician_surface():
    schema = app.openapi()
    paths = set(schema["paths"])
    assert REQUIRED_PATHS <= paths
    assert not any("technician" in path.lower() for path in paths)
    assert not any(path.startswith("/api/v1/bql") for path in paths)


def test_resident_response_schema_does_not_expose_raw_priority_or_score():
    schema = app.openapi()["components"]["schemas"]["ResidentTicketResponse"]["properties"]
    assert "priority" not in schema
    assert "score_total" not in schema
    assert "sla_due_at" not in schema
    assert "status" not in schema
    assert "classification_status" not in schema
    assert "priority_description" in schema
    assert "estimated_resolution_text" in schema
