"""Static tests for the Step 6-8 database security migration."""

import importlib.util
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = PROJECT_ROOT / "alembic" / "versions"
EXPECTED_DOWN_REVISION = "c7a3f2d9e105"
RLS_TABLES = {
    "users",
    "units",
    "user_unit_memberships",
    "technician_profiles",
    "technician_skills",
    "tickets",
    "ticket_attachments",
    "ticket_assignments",
    "ticket_status_history",
    "ai_analysis_runs",
    "ticket_scoring_results",
    "notifications",
    "audit_logs",
}


def test_exactly_one_security_migration_exists():
    assert len(_migration_files()) == 1


def test_security_migration_revision_metadata():
    module = _load_security_migration()

    assert module.down_revision == EXPECTED_DOWN_REVISION
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_security_migration_enables_and_forces_rls_on_approved_tables():
    text = _migration_text()
    module = _load_security_migration()

    assert set(module.RLS_TABLES) == RLS_TABLES
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FORCE ROW LEVEL SECURITY" in text


def test_security_migration_revokes_public_table_access():
    text = _migration_text()
    module = _load_security_migration()

    assert set(module.RLS_TABLES) == RLS_TABLES
    assert "REVOKE ALL ON TABLE" in text
    assert "FROM PUBLIC" in text


def test_security_migration_has_no_credentials_or_startup_side_effects():
    text = _migration_text().lower()

    forbidden = ["postgresql://", "supabase.co", "service_role", "password", "access_token", "authorization"]
    for value in forbidden:
        assert value not in text
    assert "create_all" not in text
    assert "fastapi" not in text
    assert "src.database" not in text


def test_security_migration_downgrade_removes_views_and_rls():
    text = _migration_text()

    assert "DROP VIEW IF EXISTS technician_ticket_view" in text
    assert "DROP VIEW IF EXISTS resident_ticket_view" in text
    assert "DROP POLICY IF EXISTS" in text
    assert "NO FORCE ROW LEVEL SECURITY" in text
    assert "DISABLE ROW LEVEL SECURITY" in text


def _migration_files() -> list[Path]:
    return sorted(VERSIONS_DIR.glob("*_add_database_security_policies_and_views.py"))


def _migration_text() -> str:
    return _migration_files()[0].read_text(encoding="utf-8")


def _load_security_migration():
    migration_file = _migration_files()[0]
    spec = importlib.util.spec_from_file_location("security_migration", migration_file)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load migration module from {migration_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy_names() -> list[str]:
    return re.findall(r"CREATE POLICY ([a-z0-9_]+)", _migration_text())
