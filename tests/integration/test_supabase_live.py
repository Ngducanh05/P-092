"""Opt-in live Supabase validation for T-006/T-007."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import jwt
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from alembic import command
from src.config import Settings, get_settings
from src.main import app
from src.security.supabase_admin import build_supabase_admin_headers

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_REQUIRED = {
    "APP_ENV": "app_env",
    "DATABASE_URL": "database_url",
    "SUPABASE_URL": "supabase_url",
    "SUPABASE_PUBLISHABLE_KEY": "supabase_publishable_key",
    "SUPABASE_SECRET_KEY": "supabase_secret_key",
    "SUPABASE_STORAGE_BUCKET": "supabase_storage_bucket",
}
BUSINESS_TABLES = {
    "residents",
    "bql_staff",
    "units",
    "resident_unit_memberships",
    "tickets",
    "ticket_attachments",
    "ticket_attachment_upload_sessions",
    "ticket_status_history",
    "notifications",
    "audit_logs",
}
FINAL_POLICY_NAMES = {
    "rls_residents_select_own_profile",
    "rls_bql_staff_select_own_profile",
    "rls_resident_unit_memberships_select_own_active",
    "rls_units_select_resident_active_membership",
    "rls_tickets_resident_select_owned",
    "rls_tickets_bql_select_all_mvp",
    "rls_ticket_attachments_select_authorized_parent",
    "rls_ticket_attachment_upload_sessions_deny_all_client_access",
}
SMALL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff"
    b"\xff?\x00\x05\xfe\x02\xfeA\xe2&\x8b\x00\x00\x00\x00IEND\xaeB`\x82"
)


@dataclass
class LiveContext:
    settings: Settings
    engine: Engine
    prefix: str
    unit_ids: list[UUID] = field(default_factory=list)
    membership_ids: list[UUID] = field(default_factory=list)
    ticket_ids: list[UUID] = field(default_factory=list)
    attachment_ids: list[UUID] = field(default_factory=list)
    upload_session_ids: list[UUID] = field(default_factory=list)
    storage_paths: list[str] = field(default_factory=list)
    created_resident_ids: list[UUID] = field(default_factory=list)

    def cleanup(self) -> None:
        with self.engine.begin() as connection:
            for attachment_id in self.attachment_ids:
                connection.execute(text("DELETE FROM ticket_attachments WHERE id = :id"), {"id": attachment_id})
            for upload_session_id in self.upload_session_ids:
                connection.execute(
                    text("DELETE FROM ticket_attachment_upload_sessions WHERE id = :id"),
                    {"id": upload_session_id},
                )
            for ticket_id in self.ticket_ids:
                connection.execute(text("DELETE FROM ticket_status_history WHERE ticket_id = :id"), {"id": ticket_id})
                connection.execute(text("DELETE FROM tickets WHERE id = :id"), {"id": ticket_id})
            for membership_id in self.membership_ids:
                connection.execute(text("DELETE FROM resident_unit_memberships WHERE id = :id"), {"id": membership_id})
            for unit_id in self.unit_ids:
                connection.execute(text("DELETE FROM units WHERE id = :id"), {"id": unit_id})
            for user_id in self.created_resident_ids:
                connection.execute(text("DELETE FROM residents WHERE id = :id"), {"id": user_id})
        self._cleanup_storage_objects()

    def _cleanup_storage_objects(self) -> None:
        if not self.storage_paths:
            return
        headers = build_supabase_admin_headers(self.settings.supabase_secret_key)
        url = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/{self.settings.supabase_storage_bucket}"
        try:
            with httpx.Client(timeout=10.0) as client:
                client.request("DELETE", url, headers=headers, json={"prefixes": self.storage_paths})
        except httpx.HTTPError:
            return


@dataclass(frozen=True)
class ResidentContext:
    user_id: UUID
    unit_id: UUID
    unowned_unit_id: UUID
    unowned_ticket_id: UUID
    unowned_attachment_id: UUID


@dataclass(frozen=True)
class UploadFlow:
    resident: ResidentContext
    upload_id: UUID
    storage_path: str
    upload_response_status: int
    ticket_id: UUID
    attachment_id: UUID
    signed_download_url: str
    signed_download_fetch_status: int


@pytest.fixture(scope="session")
def live_settings() -> Settings:
    get_settings.cache_clear()
    settings = get_settings()
    if not settings.run_supabase_integration_tests:
        pytest.skip("RUN_SUPABASE_INTEGRATION_TESTS is not enabled.")
    missing = [name for name, field_name in BASE_REQUIRED.items() if not getattr(settings, field_name)]
    if settings.app_env not in {"development", "test"}:
        missing.append("APP_ENV")
    if missing:
        pytest.fail("Missing safe Supabase integration variables: " + ", ".join(sorted(set(missing))))
    return settings


@pytest.fixture(scope="session")
def db_engine(live_settings: Settings):
    engine = create_engine(_database_url(live_settings))
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise AssertionError("Unable to connect to the configured Supabase database.") from exc
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def live_context(live_settings: Settings, db_engine: Engine):
    context = LiveContext(live_settings, db_engine, f"t006_t007_{secrets.token_hex(8)}")
    yield context
    context.cleanup()


@pytest.fixture()
def api_client(live_settings: Settings):
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def resident_token(live_settings: Settings) -> str:
    return _require_token("SUPABASE_TEST_RESIDENT_ACCESS_TOKEN")


@pytest.fixture()
def bql_token(live_settings: Settings) -> str:
    return _require_token("SUPABASE_TEST_BQL_ACCESS_TOKEN")


@pytest.fixture()
def resident_context(
    api_client: TestClient,
    db_engine: Engine,
    live_context: LiveContext,
    resident_token: str,
) -> ResidentContext:
    existed_before = _resident_exists(db_engine, _token_subject(resident_token))
    response = api_client.get("/api/v1/auth/me", headers=_bearer(resident_token))
    assert response.status_code == 200
    user_id = UUID(response.json()["id"])
    if not existed_before:
        live_context.created_resident_ids.append(user_id)

    unit_id = uuid4()
    unowned_unit_id = uuid4()
    membership_id = uuid4()
    unowned_ticket_id = uuid4()
    unowned_attachment_id = uuid4()
    with db_engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO units (id, building_code, floor, unit_number, is_active)
                VALUES (:id, :building_code, '10', '1001', true)
                """
            ),
            {"id": unit_id, "building_code": live_context.prefix},
        )
        connection.execute(
            text(
                """
                INSERT INTO units (id, building_code, floor, unit_number, is_active)
                VALUES (:id, :building_code, '99', '9901', true)
                """
            ),
            {"id": unowned_unit_id, "building_code": f"{live_context.prefix}_other"},
        )
        connection.execute(
            text(
                """
                INSERT INTO resident_unit_memberships (id, resident_id, unit_id, is_active)
                VALUES (:id, :resident_id, :unit_id, true)
                """
            ),
            {"id": membership_id, "resident_id": user_id, "unit_id": unit_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO tickets (id, resident_id, unit_id, title, description, status)
                VALUES (:id, :resident_id, :unit_id, :title, :description, 'new')
                """
            ),
            {
                "id": unowned_ticket_id,
                "resident_id": user_id,
                "unit_id": unowned_unit_id,
                "title": f"{live_context.prefix} unowned ticket",
                "description": "Live validation ticket for an unowned unit.",
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO ticket_attachments (id, ticket_id, file_url, file_type, mime_type, file_size)
                VALUES (:id, :ticket_id, :file_url, 'image', 'image/png', :file_size)
                """
            ),
            {
                "id": unowned_attachment_id,
                "ticket_id": unowned_ticket_id,
                "file_url": f"tickets/{user_id}/unowned/{uuid4()}.png",
                "file_size": len(SMALL_PNG),
            },
        )
    live_context.unit_ids.extend([unit_id, unowned_unit_id])
    live_context.membership_ids.append(membership_id)
    live_context.ticket_ids.append(unowned_ticket_id)
    live_context.attachment_ids.append(unowned_attachment_id)
    return ResidentContext(user_id, unit_id, unowned_unit_id, unowned_ticket_id, unowned_attachment_id)


@pytest.fixture(scope="session")
def bql_profile(live_context: LiveContext, db_engine: Engine, bql_token: str) -> UUID:
    user_id = _token_subject(bql_token)
    with db_engine.connect() as connection:
        exists = connection.scalar(text("SELECT true FROM bql_staff WHERE id = :id"), {"id": user_id})
    if not exists:
        pytest.fail("SUPABASE_TEST_BQL_ACCESS_TOKEN profile is not provisioned as BQL.")
    return user_id


@pytest.fixture()
def upload_flow(
    api_client: TestClient,
    db_engine: Engine,
    live_context: LiveContext,
    resident_context: ResidentContext,
    resident_token: str,
) -> UploadFlow:
    upload_response = api_client.post(
        "/api/v1/storage/ticket-attachments/upload-url",
        headers=_bearer(resident_token),
        json={"original_filename": "small.png", "mime_type": "image/png", "file_size": len(SMALL_PNG)},
    )
    assert upload_response.status_code == 200
    upload_body = upload_response.json()
    upload_id = UUID(upload_body["upload_id"])
    with db_engine.connect() as connection:
        storage_path = connection.scalar(
            text("SELECT storage_path FROM ticket_attachment_upload_sessions WHERE id = :id"),
            {"id": upload_id},
        )
    assert storage_path
    live_context.upload_session_ids.append(upload_id)
    live_context.storage_paths.append(storage_path)

    upload_status = _upload_to_signed_target(live_context.settings, storage_path, upload_body)
    ticket_response = api_client.post(
        "/api/v1/tickets",
        headers=_bearer(resident_token),
        json={
            "title": f"{live_context.prefix} uploaded attachment",
            "description": "Live validation ticket with a private uploaded PNG attachment.",
            "unit_id": str(resident_context.unit_id),
            "attachment_upload_ids": [str(upload_id)],
        },
    )
    assert ticket_response.status_code == 201
    ticket_body = ticket_response.json()
    ticket_id = UUID(ticket_body["id"])
    attachment_id = UUID(ticket_body["attachments"][0]["id"])
    live_context.ticket_ids.append(ticket_id)
    live_context.attachment_ids.append(attachment_id)

    signed_response = api_client.get(
        f"/api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url",
        headers=_bearer(resident_token),
    )
    assert signed_response.status_code == 200
    signed_download_url = signed_response.json()["signed_download_url"]
    fetch_response = httpx.get(_absolute_storage_url(live_context.settings, signed_download_url), timeout=10.0)
    return UploadFlow(
        resident=resident_context,
        upload_id=upload_id,
        storage_path=storage_path,
        upload_response_status=upload_status,
        ticket_id=ticket_id,
        attachment_id=attachment_id,
        signed_download_url=signed_download_url,
        signed_download_fetch_status=fetch_response.status_code,
    )


def test_migration_upgrade_head(live_settings: Settings):
    _require_live_migration_allowed(live_settings)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))

    command.upgrade(config, "head")


def test_database_is_at_alembic_head(db_engine: Engine):
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    script_heads = set(ScriptDirectory.from_config(config).get_heads())
    with db_engine.connect() as connection:
        db_heads = set(connection.scalars(text("SELECT version_num FROM alembic_version")).all())

    assert db_heads == script_heads


def test_required_tables_exist(db_engine: Engine):
    with db_engine.connect() as connection:
        names = set(
            connection.scalars(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
            )
        )

    assert BUSINESS_TABLES <= names


def test_profile_auth_constraints_exist(db_engine: Engine):
    with db_engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT convalidated, confrelid::regclass::text AS referenced_table
                FROM pg_constraint
                WHERE conname IN ('fk_residents_id_auth_users', 'fk_bql_staff_id_auth_users')
                """
            )
        ).all()
        index_defs = "\n".join(
            connection.scalars(
                text(
                    """
                    SELECT indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND indexname IN ('ix_residents_phone_number', 'ix_bql_staff_email')
                    """
                )
            )
        )

    assert len(rows) == 2
    assert all(row.referenced_table == "auth.users" for row in rows)
    assert "ix_residents_phone_number" in index_defs
    assert "ix_bql_staff_email" in index_defs


def test_rls_enabled_on_business_tables(db_engine: Engine):
    with db_engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT relname, relrowsecurity, relforcerowsecurity
                FROM pg_class
                JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
                WHERE pg_namespace.nspname = 'public'
                  AND relname = ANY(:table_names)
                """
            ),
            {"table_names": list(BUSINESS_TABLES)},
        ).all()

    assert {row.relname for row in rows} >= BUSINESS_TABLES
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in rows)


def test_final_rls_policies_exist(db_engine: Engine):
    with db_engine.connect() as connection:
        policies = set(
            connection.scalars(
                text(
                    """
                    SELECT policyname
                    FROM pg_policies
                    WHERE schemaname = 'public'
                    """
                )
            )
        )

    assert FINAL_POLICY_NAMES <= policies


def test_anonymous_cannot_read_business_tables(live_settings: Settings):
    headers = {"apikey": live_settings.supabase_publishable_key}
    for table_name in ("residents", "bql_staff", "units", "tickets", "ticket_attachments"):
        response = httpx.get(
            f"{live_settings.supabase_url.rstrip('/')}/rest/v1/{table_name}",
            params={"select": "id", "limit": "1"},
            headers=headers,
            timeout=10.0,
        )
        assert response.status_code in {200, 401, 403}
        if response.status_code == 200:
            assert response.json() == []


def test_private_bucket_configuration(live_settings: Settings):
    response = httpx.get(
        f"{live_settings.supabase_url.rstrip('/')}/storage/v1/bucket/{live_settings.supabase_storage_bucket}",
        headers=build_supabase_admin_headers(live_settings.supabase_secret_key),
        timeout=10.0,
    )

    assert response.status_code == 200
    assert response.json()["public"] is False


def test_resident_auth_me(api_client: TestClient, resident_context: ResidentContext, resident_token: str):
    response = api_client.get("/api/v1/auth/me", headers=_bearer(resident_token))

    assert response.status_code == 200
    assert UUID(response.json()["id"]) == resident_context.user_id
    assert response.json()["role"] == "resident"


def test_resident_can_read_own_units(api_client: TestClient, resident_context: ResidentContext, resident_token: str):
    response = api_client.get("/api/v1/units/my", headers=_bearer(resident_token))

    assert response.status_code == 200
    assert str(resident_context.unit_id) in {item["unit_id"] for item in response.json()}


def test_resident_a_cannot_read_resident_b_ticket(
    api_client: TestClient,
    resident_context: ResidentContext,
    resident_token: str,
):
    response = api_client.get(f"/api/v1/tickets/{resident_context.unowned_ticket_id}", headers=_bearer(resident_token))

    assert response.status_code == 404


def test_resident_cannot_use_unowned_unit(
    api_client: TestClient,
    resident_context: ResidentContext,
    resident_token: str,
):
    response = api_client.post(
        "/api/v1/tickets",
        headers=_bearer(resident_token),
        json={
            "title": "Unowned unit",
            "description": "This ticket should be rejected because the unit is not owned.",
            "unit_id": str(resident_context.unowned_unit_id),
        },
    )

    assert response.status_code == 404


def test_bql_auth_me(api_client: TestClient, bql_profile: UUID, bql_token: str):
    response = api_client.get("/api/v1/auth/me", headers=_bearer(bql_token))

    assert response.status_code == 200
    assert UUID(response.json()["id"]) == bql_profile
    assert response.json()["actor_type"] == "bql"


def test_bql_can_read_ticket(
    api_client: TestClient,
    bql_profile: UUID,
    resident_context: ResidentContext,
    bql_token: str,
):
    response = api_client.get(f"/api/v1/tickets/{resident_context.unowned_ticket_id}", headers=_bearer(bql_token))

    assert bql_profile
    assert response.status_code == 200
    assert response.json()["id"] == str(resident_context.unowned_ticket_id)


def test_non_bql_cannot_call_bql_route(api_client: TestClient, resident_token: str):
    response = api_client.get("/api/v1/bql/tickets", headers=_bearer(resident_token))

    assert response.status_code == 403


def test_create_signed_upload_target(upload_flow: UploadFlow):
    assert upload_flow.upload_id
    assert upload_flow.storage_path.startswith(f"tickets/{upload_flow.resident.user_id}/")


def test_upload_small_png(upload_flow: UploadFlow):
    assert upload_flow.upload_response_status in {200, 201}


def test_upload_session_created(db_engine: Engine, upload_flow: UploadFlow):
    with db_engine.connect() as connection:
        row = connection.execute(
            text("SELECT resident_id, status FROM ticket_attachment_upload_sessions WHERE id = :id"),
            {"id": upload_flow.upload_id},
        ).one()

    assert row.resident_id == upload_flow.resident.user_id
    assert row.status in {"pending", "consumed"}


def test_create_ticket_consumes_upload_session(db_engine: Engine, upload_flow: UploadFlow):
    with db_engine.connect() as connection:
        row = connection.execute(
            text("SELECT status, consumed_at, object_verified_at FROM ticket_attachment_upload_sessions WHERE id = :id"),
            {"id": upload_flow.upload_id},
        ).one()

    assert row.status == "consumed"
    assert row.consumed_at is not None
    assert row.object_verified_at is not None


def test_attachment_metadata_persisted(db_engine: Engine, upload_flow: UploadFlow):
    with db_engine.connect() as connection:
        row = connection.execute(
            text("SELECT ticket_id, file_url, mime_type, file_size FROM ticket_attachments WHERE id = :id"),
            {"id": upload_flow.attachment_id},
        ).one()

    assert row.ticket_id == upload_flow.ticket_id
    assert row.file_url == upload_flow.storage_path
    assert row.mime_type == "image/png"
    assert row.file_size == len(SMALL_PNG)


def test_signed_download_url_is_authorized(upload_flow: UploadFlow):
    assert upload_flow.signed_download_url
    assert upload_flow.storage_path not in upload_flow.signed_download_url


def test_signed_download_url_fetches_object(upload_flow: UploadFlow):
    assert upload_flow.signed_download_fetch_status == 200


def test_unauthorized_attachment_download_returns_404(
    api_client: TestClient,
    resident_context: ResidentContext,
    resident_token: str,
):
    response = api_client.get(
        f"/api/v1/tickets/{resident_context.unowned_ticket_id}/attachments/"
        f"{resident_context.unowned_attachment_id}/download-url",
        headers=_bearer(resident_token),
    )

    assert response.status_code == 404


def test_resident_rls_cannot_read_unowned_ticket_via_postgrest(
    live_settings: Settings,
    resident_context: ResidentContext,
    resident_token: str,
):
    response = httpx.get(
        f"{live_settings.supabase_url.rstrip('/')}/rest/v1/tickets",
        params={"select": "id", "id": f"eq.{resident_context.unowned_ticket_id}"},
        headers={**_bearer(resident_token), "apikey": live_settings.supabase_publishable_key},
        timeout=10.0,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_security_invoker_views_exist(db_engine: Engine):
    with db_engine.connect() as connection:
        options = dict(
            connection.execute(
                text(
                """
                    SELECT pg_class.relname, pg_class.reloptions
                    FROM pg_class
                    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
                    WHERE pg_namespace.nspname = 'public'
                      AND pg_class.relkind = 'v'
                      AND pg_class.relname IN ('resident_ticket_view')
                    """
                )
            )
        )

    assert set(options) == {"resident_ticket_view"}
    assert all("security_invoker=true" in (value or "") for value in options.values())


def _require_token(name: str) -> str:
    token = os.getenv(name)
    if not token:
        pytest.skip(f"BLOCKED â€” MISSING TEST TOKEN: {name}")
    return token


def _require_live_migration_allowed(settings: Settings) -> None:
    if not settings.allow_live_migration:
        pytest.fail("Missing safe Supabase integration variables: ALLOW_LIVE_MIGRATION")


def _database_url(settings: Settings) -> str:
    database_url = settings.require_database_url()
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token_subject(token: str) -> UUID:
    claims = jwt.decode(token, options={"verify_signature": False, "verify_aud": False, "verify_exp": False})
    return UUID(str(claims["sub"]))


def _resident_exists(engine: Engine, user_id: UUID) -> bool:
    with engine.connect() as connection:
        return bool(connection.scalar(text("SELECT true FROM residents WHERE id = :id"), {"id": user_id}))


def _upload_to_signed_target(settings: Settings, storage_path: str, upload_body: dict[str, object]) -> int:
    headers = dict(upload_body.get("required_headers") or {})
    headers.setdefault("content-type", "image/png")
    signed_url = upload_body.get("signed_upload_url")
    token = upload_body.get("signed_upload_token")
    if signed_url:
        response = httpx.put(_absolute_storage_url(settings, str(signed_url)), content=SMALL_PNG, headers=headers, timeout=10.0)
        if response.status_code not in {200, 201, 204, 405}:
            return response.status_code
        if response.status_code != 405:
            return response.status_code
    if not token:
        pytest.fail("Signed upload target did not include a usable upload token.")
    response = httpx.put(
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/upload/sign/"
        f"{settings.supabase_storage_bucket}/{storage_path}",
        params={"token": str(token)},
        content=SMALL_PNG,
        headers=headers,
        timeout=10.0,
    )
    return response.status_code


def _absolute_storage_url(settings: Settings, signed_url: str) -> str:
    if signed_url.startswith("http://") or signed_url.startswith("https://"):
        return signed_url
    if signed_url.startswith("/storage/v1/"):
        return f"{settings.supabase_url.rstrip('/')}{signed_url}"
    if signed_url.startswith("/"):
        return f"{settings.supabase_url.rstrip('/')}/storage/v1{signed_url}"
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/{signed_url}"

