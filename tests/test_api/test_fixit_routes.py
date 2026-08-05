"""FixIt API route tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.api.dependencies.auth import get_current_user, get_supabase_jwt_verifier
from src.api.dependencies.database import get_db
from src.api.routes.storage import get_storage_service
from src.database.models.attachment import TicketAttachment
from src.database.models.ticket import Ticket
from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession
from src.database.models.unit import Unit
from src.database.models.user import User
from src.database.models.user_unit_membership import UserUnitMembership
from src.main import app
from src.models.api.errors import AUTH_TOKEN_INVALID, USER_INACTIVE, DomainError
from src.models.enums import Role, TicketStatus
from src.services.storage_service import SignedUploadTarget


def test_required_paths_exist_in_openapi():
    paths = set(app.openapi()["paths"])

    assert "/api/v1/auth/me" in paths
    assert "/api/v1/units/my" in paths
    assert "/api/v1/storage/ticket-attachments/upload-url" in paths
    assert "/api/v1/tickets" in paths
    assert "/api/v1/tickets/my" in paths
    assert "/api/v1/tickets/{ticket_id}" in paths
    assert "/api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url" in paths
    assert "/api/v1/coordinator/tickets" in paths
    assert "/health" in paths
    assert "/ready" in paths
    assert "/api/v1/chat" not in paths
    assert "/api/v1/status" not in paths


@pytest.mark.asyncio
async def test_units_requires_auth(client):
    response = await client.get("/api/v1/units/my")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_MISSING"
    assert response.json()["error"]["request_id"]


@pytest.mark.asyncio
async def test_invalid_token_uses_stable_error_contract(client):
    class RejectingVerifier:
        def verify(self, token):
            raise DomainError(AUTH_TOKEN_INVALID, "Invalid access token.", 401)

    app.dependency_overrides[get_supabase_jwt_verifier] = lambda: RejectingVerifier()
    try:
        response = await client.get("/api/v1/units/my", headers={"Authorization": "Bearer invalid"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["error"]["code"] == AUTH_TOKEN_INVALID
    assert response.headers["x-request-id"] == response.json()["error"]["request_id"]


@pytest.mark.asyncio
async def test_inactive_user_error_contract(client):
    def inactive_user():
        raise DomainError(USER_INACTIVE, "User is inactive.", 403)

    app.dependency_overrides[get_current_user] = inactive_user
    try:
        response = await client.get("/api/v1/units/my")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == USER_INACTIVE


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


@pytest.mark.asyncio
async def test_ready_success_uses_safe_statuses(client, monkeypatch):
    def ready_check(self):
        return (
            {
                "status": "ready",
                "checks": {
                    "database": "ok",
                    "migration": "ok",
                    "supabase_auth": "configured",
                    "supabase_storage": "configured",
                },
            },
            200,
        )

    monkeypatch.setattr("src.main.ReadinessService.check", ready_check)

    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "http" not in str(response.json()).lower()


@pytest.mark.asyncio
async def test_ready_failure_returns_503_without_stack_traces(client, monkeypatch):
    def ready_check(self):
        return (
            {
                "status": "not_ready",
                "checks": {
                    "database": "error",
                    "migration": "unknown",
                    "supabase_auth": "missing",
                    "supabase_storage": "missing",
                },
            },
            503,
        )

    monkeypatch.setattr("src.main.ReadinessService.check", ready_check)

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "error"
    assert "traceback" not in str(response.json()).lower()


@pytest.mark.asyncio
async def test_auth_me_and_units_success(client, db_session):
    resident = _resident()
    unit = _unit()
    db_session.add_all([resident, unit, _membership(resident.id, unit.id)])
    db_session.commit()
    _override_auth_and_db(resident, db_session)
    try:
        me_response = await client.get("/api/v1/auth/me")
        units_response = await client.get("/api/v1/units/my")
    finally:
        app.dependency_overrides.clear()

    assert me_response.status_code == 200
    assert me_response.json()["id"] == str(resident.id)
    assert me_response.json()["active_unit_memberships"][0]["unit_id"] == str(unit.id)
    assert units_response.status_code == 200
    assert units_response.json()[0]["unit_id"] == str(unit.id)


@pytest.mark.asyncio
async def test_signed_upload_creates_upload_session_without_raw_path(client, db_session):
    resident = _resident()
    db_session.add(resident)
    db_session.commit()

    class FakeStorage:
        def create_signed_upload_target(self, user_id, request):
            return SignedUploadTarget(
                storage_path=f"tickets/{user_id}/2026/08/{uuid4()}.jpg",
                signed_upload_url="https://storage.example/upload",
                signed_upload_token=None,
                expires_in=7200,
                required_headers={"content-type": request.mime_type},
            )

    _override_auth_and_db(resident, db_session)
    app.dependency_overrides[get_storage_service] = lambda: FakeStorage()
    try:
        response = await client.post(
            "/api/v1/storage/ticket-attachments/upload-url",
            json={"original_filename": "photo.jpg", "mime_type": "image/jpeg", "file_size": 128},
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    upload_session = db_session.query(TicketAttachmentUploadSession).one()
    assert response.status_code == 200
    assert body["upload_id"] == str(upload_session.id)
    assert "storage_path" not in body
    assert upload_session.status == "pending"
    assert upload_session.storage_path.startswith(f"tickets/{resident.id}/")


@pytest.mark.asyncio
async def test_ticket_create_list_detail_and_coordinator_list(client, db_session):
    resident = _resident()
    coordinator = User(id=uuid4(), email="coordinator@example.com", role=Role.COORDINATOR, is_active=True)
    unit = _unit()
    db_session.add_all([resident, coordinator, unit, _membership(resident.id, unit.id)])
    db_session.commit()
    _override_auth_and_db(resident, db_session)
    try:
        create_response = await client.post(
            "/api/v1/tickets",
            json={"title": "Leak under sink", "description": "Water has been leaking under the sink all morning."},
        )
        list_response = await client.get("/api/v1/tickets/my")
        ticket_id = create_response.json()["id"]
        detail_response = await client.get(f"/api/v1/tickets/{ticket_id}")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["status"] == TicketStatus.NEW.value
    assert create_response.json()["attachments"] == []
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == ticket_id

    _override_auth_and_db(coordinator, db_session)
    try:
        coordinator_response = await client.get("/api/v1/coordinator/tickets")
    finally:
        app.dependency_overrides.clear()

    assert coordinator_response.status_code == 200
    assert coordinator_response.json()["total"] == 1


@pytest.mark.asyncio
async def test_attachment_download_url_authorized_and_no_raw_path(client, db_session, monkeypatch):
    resident = _resident()
    unit = _unit()
    ticket = Ticket(
        resident_id=resident.id,
        unit_id=unit.id,
        title="Broken pipe",
        description="A broken pipe is leaking in the hallway.",
        status=TicketStatus.NEW,
    )
    attachment = TicketAttachment(
        ticket=ticket,
        file_url=f"tickets/{resident.id}/2026/08/{uuid4()}.jpg",
        file_type="image",
        mime_type="image/jpeg",
        file_size=512,
    )
    db_session.add_all([resident, unit, _membership(resident.id, unit.id), ticket, attachment])
    db_session.commit()

    class FakeStorage:
        settings = type("Settings", (), {"supabase_signed_download_ttl_seconds": 123})()

        def create_signed_download_url(self, storage_path):
            assert storage_path == attachment.file_url
            return "https://storage.example/download"

    monkeypatch.setattr("src.services.ticket_service.StorageService", lambda: FakeStorage())
    _override_auth_and_db(resident, db_session)
    try:
        detail_response = await client.get(f"/api/v1/tickets/{ticket.id}")
        download_response = await client.get(f"/api/v1/tickets/{ticket.id}/attachments/{attachment.id}/download-url")
    finally:
        app.dependency_overrides.clear()

    assert detail_response.status_code == 200
    attachment_body = detail_response.json()["attachments"][0]
    assert "storage_path" not in attachment_body
    assert attachment_body["downloadable"] is True
    assert attachment_body["download_url_endpoint"].endswith(f"/attachments/{attachment.id}/download-url")
    assert download_response.status_code == 200
    assert download_response.json()["attachment_id"] == str(attachment.id)
    assert download_response.json()["signed_download_url"] == "https://storage.example/download"


def _override_auth_and_db(user: User, db_session) -> None:
    app.dependency_overrides[get_current_user] = lambda: user

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db


def _resident() -> User:
    return User(id=uuid4(), email="resident@example.com", role=Role.RESIDENT, is_active=True)


def _unit() -> Unit:
    return Unit(id=uuid4(), building_code="A", floor="10", unit_number="1001", is_active=True)


def _membership(user_id, unit_id) -> UserUnitMembership:
    return UserUnitMembership(
        id=uuid4(),
        user_id=user_id,
        unit_id=unit_id,
        is_active=True,
        linked_at=datetime.now(UTC) - timedelta(days=1),
    )
