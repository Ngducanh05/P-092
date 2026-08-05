"""FixIt API route tests."""

from uuid import uuid4

import pytest

from src.api.dependencies.auth import get_current_user
from src.database.models.user import User
from src.main import app
from src.models.enums import Role


def test_required_paths_exist_in_openapi():
    paths = set(app.openapi()["paths"])

    assert "/api/v1/auth/me" in paths
    assert "/api/v1/units/my" in paths
    assert "/api/v1/storage/ticket-attachments/upload-url" in paths
    assert "/api/v1/tickets" in paths
    assert "/api/v1/tickets/my" in paths
    assert "/api/v1/tickets/{ticket_id}" in paths
    assert "/api/v1/coordinator/tickets" in paths
    assert "/health" in paths


@pytest.mark.asyncio
async def test_units_requires_auth(client):
    response = await client.get("/api/v1/units/my")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_MISSING"


@pytest.mark.asyncio
async def test_role_forbidden_error_contract(client):
    user = User(id=uuid4(), email="coordinator@example.com", role=Role.COORDINATOR, is_active=True)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        response = await client.get("/api/v1/units/my")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_FORBIDDEN"
