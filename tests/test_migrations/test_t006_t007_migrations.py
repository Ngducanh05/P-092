"""Static tests for T-006/T-007 migrations."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = PROJECT_ROOT / "alembic" / "versions"


def test_supabase_user_alignment_migration_exists_and_is_chained():
    text = (VERSIONS_DIR / "a1b2c3d4e5f6_align_users_with_supabase_auth.py").read_text(encoding="utf-8")

    assert 'revision: str = "a1b2c3d4e5f6"' in text
    assert 'down_revision: str | Sequence[str] | None = "f4d1c8b2a609"' in text
    assert "phone_number" in text
    assert "ix_users_email_not_null" in text
    assert "ix_users_phone_number_not_null" in text
    assert "ck_users_email_or_phone" in text
    assert "auth.users" in text


def test_rls_identity_migration_replaces_placeholder_policies():
    text = (VERSIONS_DIR / "b2c3d4e5f6a7_bind_supabase_auth_identity_policies.py").read_text(encoding="utf-8")

    assert 'down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"' in text
    created_policy_text = "\n".join(line for line in text.splitlines() if "CREATE POLICY" in line)
    assert "pending_identity" not in created_policy_text
    assert "NULL::uuid" not in text
    assert "(select auth.uid())" in text
    assert "TO authenticated" in text
    assert "membership.is_active = true" in text
    assert "assignment.is_active = true" in text
    assert "app_user.role = 'coordinator'" in text
    assert "service_role" not in text
