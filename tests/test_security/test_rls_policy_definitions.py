"""Static tests for final Resident/BQL RLS policy definitions."""

import re

from tests.test_security.test_security_migration import _migration_text, policy_names


def test_policy_names_are_stable_and_unique():
    names = policy_names()

    assert names
    assert all(name.startswith("rls_") for name in names)
    assert len(names) == len(set(names))


def test_resident_ticket_policy_references_active_membership_ownership():
    policy = _policy("rls_tickets_resident_select_owned")

    assert "resident_unit_memberships membership" in policy
    assert "membership.unit_id = tickets.unit_id" in policy
    assert "membership.resident_id = (SELECT auth.uid())" in policy
    assert "membership.is_active = true" in policy


def test_bql_ticket_policy_references_active_bql_staff():
    policy = _policy("rls_tickets_bql_select_all_mvp")

    assert "FROM bql_staff" in policy
    assert "bql_staff.id = (SELECT auth.uid())" in policy
    assert "bql_staff.is_active = true" in policy


def test_attachment_and_status_history_follow_authorized_parent_ticket():
    attachment_policy = _policy(
        "rls_ticket_attachments_select_authorized_parent"
    )
    history_policy = _policy(
        "rls_ticket_status_history_select_authorized_parent"
    )

    assert "tickets.id = ticket_attachments.ticket_id" in attachment_policy
    assert "tickets.id = ticket_status_history.ticket_id" in history_policy


def test_notification_policy_references_recipient_auth_ownership():
    policy = _policy("rls_notifications_recipient_auth_select_owned")

    assert "recipient_auth_user_id = (SELECT auth.uid())" in policy


def test_upload_sessions_are_explicitly_denied_to_direct_clients():
    policy = _policy(
        "rls_ticket_attachment_upload_sessions_deny_all_client_access"
    )

    assert "FOR ALL" in policy
    assert "TO anon, authenticated" in policy
    assert "USING (false)" in policy
    assert "WITH CHECK (false)" in policy


def test_internal_ai_scoring_and_audit_tables_are_client_denied():
    for policy_name in (
        "rls_ai_analysis_runs_deny_all_client_access",
        "rls_ticket_scoring_results_deny_all_client_access",
        "rls_audit_logs_deny_all_client_access",
    ):
        policy = _policy(policy_name)
        assert "FOR ALL" in policy
        assert "TO anon, authenticated" in policy
        assert "USING (false)" in policy
        assert "WITH CHECK (false)" in policy


def test_no_technician_or_coordinator_policy_remains():
    names = policy_names()
    policy_sql = "\n".join(_policy(name) for name in names)

    assert all("technician" not in name for name in names)
    assert all("coordinator" not in name for name in names)
    assert "CREATE POLICY rls_tickets_technician" not in policy_sql
    assert "role" not in policy_sql.casefold()


def _policy(name: str) -> str:
    text = _migration_text()
    match = re.search(
        rf"CREATE POLICY {name}.*?;",
        text,
        flags=re.DOTALL,
    )
    if not match:
        raise AssertionError(f"Policy not found: {name}")
    return match.group(0)
