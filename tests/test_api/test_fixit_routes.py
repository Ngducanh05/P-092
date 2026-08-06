"""FixIt API route tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.api.dependencies.auth import CurrentActor, get_current_actor, get_supabase_jwt_verifier
from src.api.dependencies.database import get_db
from src.api.routes.storage import get_storage_service
from src.database.models.attachment import TicketAttachment
from src.database.models.bql_staff import BQLStaff
from src.database.models.resident import Resident
from src.database.models.resident_unit_membership import ResidentUnitMembership
from src.database.models.ticket import Ticket
from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession
from src.database.models.unit import Unit
from src.main import app
from src.models.api.errors import ACTOR_FORBIDDEN, AUTH_TOKEN_INVALID, USER_INACTIVE, DomainError
from src.models.enums import TicketStatus
from src.security.supabase_jwt import AuthenticatedPrincipal
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
    assert "/api/v1/bql/tickets" in paths
    assert "/api/v1/coordinator/tickets" not in paths
    assert "/health" in paths
    assert "/ready" in paths


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
async def test_inactive_actor_error_contract(client):
    def inactive_actor():
        raise DomainError(USER_INACTIVE, "Resident is inactive.", 403)

    app.dependency_overrides[get_current_actor] = inactive_actor
    try:
        response = await client.get("/api/v1/units/my")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == USER_INACTIVE


@pytest.mark.asyncio
async def test_actor_forbidden_error_contract(client):
    bql_staff = BQLStaff(id=uuid4(), email="bql@example.com", is_active=True)
    app.dependency_overrides[get_current_actor] = lambda: _actor("bql", bql_staff)
    try:
        response = await client.get("/api/v1/units/my")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == ACTOR_FORBIDDEN


@pytest.mark.asyncio
async def test_auth_me_and_units_success(client, db_session):
    resident = _resident()
    unit = _unit()
    db_session.add_all([resident, unit, _membership(resident.id, unit.id)])
    db_session.commit()
    _override_auth_and_db(_actor("resident", resident), db_session)
    try:
        me_response = await client.get("/api/v1/auth/me")
        units_response = await client.get("/api/v1/units/my")
    finally:
        app.dependency_overrides.clear()

    assert me_response.status_code == 200
    assert me_response.json()["actor_type"] == "resident"
    assert me_response.json()["id"] == str(resident.id)
    assert me_response.json()["active_unit_memberships"][0]["unit_id"] == str(unit.id)
    assert units_response.status_code == 200
    assert units_response.json()[0]["unit_id"] == str(unit.id)


@pytest.mark.asyncio
async def test_bql_auth_me_success(client, db_session):
    bql_staff = BQLStaff(id=uuid4(), email="bql@example.com", full_name="BQL Staff", is_active=True)
    db_session.add(bql_staff)
    db_session.commit()
    _override_auth_and_db(_actor("bql", bql_staff), db_session)
    try:
        response = await client.get("/api/v1/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "actor_type": "bql",
        "id": str(bql_staff.id),
        "email": bql_staff.email,
        "full_name": "BQL Staff",
        "is_active": True,
    }


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

    _override_auth_and_db(_actor("resident", resident), db_session)
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
async def test_ticket_create_list_detail_and_bql_list(client, db_session):
    resident = _resident()
    bql_staff = BQLStaff(id=uuid4(), email="bql@example.com", is_active=True)
    unit = _unit()
    db_session.add_all([resident, bql_staff, unit, _membership(resident.id, unit.id)])
    db_session.commit()
    _override_auth_and_db(_actor("resident", resident), db_session)
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

    _override_auth_and_db(_actor("bql", bql_staff), db_session)
    try:
        bql_response = await client.get("/api/v1/bql/tickets")
    finally:
        app.dependency_overrides.clear()

    assert bql_response.status_code == 200
    assert bql_response.json()["total"] == 1


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
    _override_auth_and_db(_actor("resident", resident), db_session)
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


def _override_auth_and_db(actor: CurrentActor, db_session) -> None:
    app.dependency_overrides[get_current_actor] = lambda: actor

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db


def _actor(actor_type, profile) -> CurrentActor:
    return CurrentActor(
        actor_type=actor_type,
        profile=profile,
        principal=AuthenticatedPrincipal(
            auth_user_id=profile.id,
            email=getattr(profile, "email", None),
            phone=getattr(profile, "phone_number", None),
            issuer="https://example.supabase.co/auth/v1",
            audience="authenticated",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        ),
    )


def _resident() -> Resident:
    return Resident(id=uuid4(), phone_number=f"+8490{uuid4().int % 10_000_000:07d}", is_active=True)


def _unit() -> Unit:
    return Unit(id=uuid4(), building_code="A", floor="10", unit_number="1001", is_active=True)


def _membership(resident_id, unit_id) -> ResidentUnitMembership:
    return ResidentUnitMembership(
        id=uuid4(),
        resident_id=resident_id,
        unit_id=unit_id,
        is_active=True,
        linked_at=datetime.now(UTC) - timedelta(days=1),
    )
