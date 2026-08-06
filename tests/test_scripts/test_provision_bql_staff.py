"""Tests for the backend-only BQL provisioning script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "provision_bql_staff.py"


def test_parser_has_no_role_or_technician_option():
    module = _load_script()
    option_strings = {
        option
        for action in module.parser()._actions
        for option in action.option_strings
    }

    assert "--role" not in option_strings
    assert "--technician" not in option_strings


def test_provision_dry_run_does_not_require_secret_password_or_network(
    monkeypatch,
    capsys,
):
    module = _load_script()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "provision",
            "--email",
            "BQL@Example.com",
            "--dry-run",
        ],
    )
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: pytest.fail("dry-run must not load secrets or database settings"),
    )
    monkeypatch.setattr(
        module.getpass,
        "getpass",
        lambda _prompt: pytest.fail("dry-run must not prompt for a password"),
    )

    assert module.main() == 0
    output = capsys.readouterr().out
    assert "DRY RUN" in output
    assert "bql@example.com" in output
    assert "secret" not in output.casefold()
    assert "password" not in output.casefold()


def test_sync_validates_auth_user_before_database_upsert(monkeypatch):
    module = _load_script()
    auth_user_id = uuid4()
    calls: list[str] = []

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "sync",
            "--auth-user-id",
            str(auth_user_id),
            "--email",
            "bql@example.com",
        ],
    )

    def fake_fetch(requested_id: UUID):
        calls.append("fetch")
        assert requested_id == auth_user_id
        return module.SupabaseAuthUser(
            id=auth_user_id,
            email="bql@example.com",
        )

    def fake_upsert(**kwargs):
        calls.append("upsert")
        assert kwargs["auth_user_id"] == auth_user_id
        assert kwargs["email"] == "bql@example.com"
        assert kwargs["dry_run"] is False

    monkeypatch.setattr(module, "fetch_auth_user", fake_fetch)
    monkeypatch.setattr(module, "upsert_bql_staff", fake_upsert)

    assert module.main() == 0
    assert calls == ["fetch", "upsert"]


def test_sync_rejects_auth_email_mismatch(monkeypatch):
    module = _load_script()
    auth_user_id = uuid4()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "sync",
            "--auth-user-id",
            str(auth_user_id),
            "--email",
            "requested@example.com",
        ],
    )
    monkeypatch.setattr(
        module,
        "fetch_auth_user",
        lambda _auth_user_id: module.SupabaseAuthUser(
            id=auth_user_id,
            email="actual@example.com",
        ),
    )
    monkeypatch.setattr(
        module,
        "upsert_bql_staff",
        lambda **_kwargs: pytest.fail("mismatched Auth user must not be upserted"),
    )

    with pytest.raises(SystemExit, match="does not match"):
        module.main()


def test_auth_payload_requires_matching_valid_id_and_email():
    module = _load_script()
    auth_user_id = uuid4()

    result = module._validated_auth_user_payload(
        {"id": str(auth_user_id), "email": "BQL@Example.com"},
        expected_email="bql@example.com",
    )

    assert result.id == auth_user_id
    assert result.email == "bql@example.com"

    with pytest.raises(SystemExit, match="does not match"):
        module._validated_auth_user_payload(
            {"id": str(auth_user_id), "email": "other@example.com"},
            expected_email="bql@example.com",
        )


def test_source_uses_parameterized_sql_and_contains_no_role_argument():
    text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "--role" not in text
    assert "technician" not in text.casefold()
    assert "WHERE id = :id" in text
    assert "VALUES (:id, :email, :full_name, true)" in text
    assert "build_supabase_admin_headers" in text


def _load_script():
    spec = importlib.util.spec_from_file_location(
        f"provision_bql_staff_test_{uuid4().hex}",
        SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load script: {SCRIPT_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
