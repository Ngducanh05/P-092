"""Static tests for the final Resident/BQL security migration."""

import importlib.util
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = PROJECT_ROOT / "alembic" / "versions"
EXPECTED_DOWN_REVISION = "d4e5f6a7b8c9"
RLS_TABLES = {
    "residents",
    "bql_staff",
    "resident_unit_memberships",
    "units",
    "tickets",
    "ticket_attachments",
    "ticket_attachment_upload_sessions",
    "ticket_status_history",
    "ai_analysis_runs",
    "ticket_scoring_results",
    "notifications",
    "audit_logs",
}


def test_final_actor_cleanup_migration_exists():
    assert len(_migration_files()) == 1


def test_final_actor_cleanup_revision_metadata():
    module = _load_security_migration()

    assert module.down_revision == EXPECTED_DOWN_REVISION
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_final_migration_enables_and_forces_rls_on_approved_tables():
    text = _migration_text()

    for table_name in RLS_TABLES:
        assert f'"{table_name}"' in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FORCE ROW LEVEL SECURITY" in text
    assert "REVOKE ALL ON TABLE" in text
    assert "FROM PUBLIC" in text


def test_final_migration_has_preflight_counts_without_private_values():
    text = _migration_text()

    for counter_name in (
        "technician_profile_count",
        "technician_skill_count",
        "ticket_assignment_count",
        "invalid_ticket_count",
        "invalid_upload_session_count",
    ):
        assert counter_name in text
    assert "SELECT *" not in text


def test_final_migration_removes_technician_and_generic_user_artifacts():
    text = _migration_text()

    assert "DROP VIEW IF EXISTS public.technician_ticket_view" in text
    assert "DROP TABLE IF EXISTS public.ticket_assignments" in text
    assert "DROP TABLE IF EXISTS public.technician_skills" in text
    assert "DROP TABLE IF EXISTS public.technician_profiles" in text
    assert 'op.drop_table("user_unit_memberships")' in text
    assert 'op.drop_table("users")' in text
    assert "DROP TYPE IF EXISTS role_enum" in text


def test_final_migration_has_no_credentials_or_startup_side_effects():
    text = _migration_text().lower()

    forbidden = ["postgresql://", "supabase.co", "service_role", "password", "access_token", "authorization"]
    for value in forbidden:
        assert value not in text
    assert "create_all" not in text
    assert "fastapi" not in text
    assert "src.database" not in text


def _migration_files() -> list[Path]:
    return sorted(VERSIONS_DIR.glob("*_remove_generic_users_and_technician_workflow.py"))


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
