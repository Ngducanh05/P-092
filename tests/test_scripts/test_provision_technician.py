"""Tests for the backend-only Technician provisioning script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "provision_technician.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        f"provision_technician_test_{uuid4().hex}",
        SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load script: {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parser_requires_auth_user_id():
    module = _load_script()
    arg_parser = module.parser()
    action_args = [a for a in arg_parser._actions if getattr(a, "dest", None) == "auth_user_id"]
    assert action_args, "--auth-user-id must be declared"
    assert action_args[0].required is True


def test_parser_has_no_password_argument():
    module = _load_script()
    option_strings = {
        opt
        for action in module.parser()._actions
        for opt in action.option_strings
    }
    assert "--password" not in option_strings
    assert "-p" not in option_strings


def test_provision_dry_run_prints_without_hitting_network_or_db(monkeypatch, capsys):
    module = _load_script()
    monkeypatch.setattr(
        sys, "argv",
        [str(SCRIPT_PATH), "provision", "--auth-user-id", str(uuid4()),
         "--email", "Tech@Example.COM", "--dry-run"],
    )
    monkeypatch.setattr(
        module, "get_settings",
        lambda: pytest.fail("dry-run must not load secrets or database settings"),
    )
    assert module.main() == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "secret" not in out.casefold()
    assert "password" not in out.casefold()


def test_provision_validates_auth_user_before_db_upsert(monkeypatch):
    module = _load_script()
    uid = uuid4()
    calls: list[str] = []

    monkeypatch.setattr(
        sys, "argv",
        [str(SCRIPT_PATH), "provision", "--auth-user-id", str(uid),
         "--email", "tech@example.com"],
    )

    def fake_fetch(requested_id):
        calls.append("fetch")
        assert requested_id == uid
        return module.SupabaseAuthUser(id=uid, email="tech@example.com")

    def fake_upsert(**kwargs):
        calls.append("upsert")
        assert kwargs["auth_user_id"] == uid
        assert kwargs["email"] == "tech@example.com"
        assert kwargs["dry_run"] is False

    monkeypatch.setattr(module, "fetch_auth_user", fake_fetch)
    monkeypatch.setattr(module, "upsert_technician", fake_upsert)
    assert module.main() == 0
    assert calls == ["fetch", "upsert"]


def test_provision_rejects_auth_email_mismatch(monkeypatch):
    module = _load_script()
    uid = uuid4()

    monkeypatch.setattr(
        sys, "argv",
        [str(SCRIPT_PATH), "provision", "--auth-user-id", str(uid),
         "--email", "requested@example.com"],
    )
    monkeypatch.setattr(
        module, "fetch_auth_user",
        lambda _id: module.SupabaseAuthUser(id=uid, email="actual@example.com"),
    )
    monkeypatch.setattr(
        module, "upsert_technician",
        lambda **_: pytest.fail("mismatched Auth user must not be upserted"),
    )
    with pytest.raises(SystemExit, match="does not match"):
        module.main()


def test_deactivate_dry_run(monkeypatch, capsys):
    module = _load_script()
    uid = uuid4()
    monkeypatch.setattr(
        sys, "argv",
        [str(SCRIPT_PATH), "deactivate", "--auth-user-id", str(uid),
         "--email", "tech@example.com", "--dry-run"],
    )
    assert module.main() == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out


def test_source_uses_parameterized_sql_and_no_password():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "WHERE id = :id" in text
    assert ":id" in text
    assert "build_supabase_admin_headers" in text
    assert "--password" not in text
    assert "password =" not in text.casefold()
    assert "password:" not in text.casefold()


def test_normalize_email_casefolding():
    module = _load_script()
    assert module._normalize_email("  Tech@Example.COM  ") == "tech@example.com"


def test_normalize_email_invalid_raises():
    module = _load_script()
    with pytest.raises(SystemExit):
        module._normalize_email("not-an-email")


def test_validated_auth_user_payload_accepts_valid():
    module = _load_script()
    uid = uuid4()
    result = module._validated_auth_user_payload(
        {"id": str(uid), "email": "TECH@EXAMPLE.COM"},
        expected_id=uid,
    )
    assert result.id == uid
    assert result.email == "tech@example.com"


def test_validated_auth_user_payload_rejects_id_mismatch():
    module = _load_script()
    uid = uuid4()
    with pytest.raises(SystemExit):
        module._validated_auth_user_payload(
            {"id": str(uuid4()), "email": "tech@example.com"},
            expected_id=uid,
        )
