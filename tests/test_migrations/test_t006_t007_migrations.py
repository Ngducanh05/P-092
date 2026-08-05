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
    upgrade_text = text.split("def upgrade()", maxsplit=1)[1].split("def downgrade()", maxsplit=1)[0]

    assert 'down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"' in text
    created_policy_text = "\n".join(line for line in upgrade_text.splitlines() if "CREATE POLICY" in line)
    assert "pending_identity" not in created_policy_text
    assert "NULL::uuid" not in upgrade_text
    assert "(select auth.uid())" in upgrade_text
    assert "TO authenticated" in upgrade_text
    assert "membership.is_active = true" in upgrade_text
    assert "assignment.is_active = true" in upgrade_text
    assert "app_user.role = 'coordinator'" in upgrade_text
    assert "service_role" not in upgrade_text


def test_rls_identity_migration_downgrade_restores_previous_policies():
    text = (VERSIONS_DIR / "b2c3d4e5f6a7_bind_supabase_auth_identity_policies.py").read_text(encoding="utf-8")

    assert "OLD_POLICY_SQL" in text
    assert "rls_users_deny_all" in text
    assert "rls_tickets_resident_select_owned_pending_identity" in text
    assert "for policy_sql in OLD_POLICY_SQL" in text


def test_upload_session_completion_migration_is_chained_and_safe():
    text = (VERSIONS_DIR / "c3d4e5f6a7b8_complete_t006_t007_upload_sessions.py").read_text(encoding="utf-8")

    assert 'revision: str = "c3d4e5f6a7b8"' in text
    assert 'down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"' in text
    assert "ticket_attachment_upload_sessions" in text
    assert "ck_users_phone_number_e164" in text
    assert "VALIDATE CONSTRAINT fk_users_id_auth_users" in text
    assert "orphan_count" in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "FOR ALL TO anon, authenticated" in text
    assert "USING (false)" in text
    assert "DROP POLICY IF EXISTS" in text
    assert "op.drop_table(\"ticket_attachment_upload_sessions\")" in text
