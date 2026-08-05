"""Static tests for RLS policy definitions."""

import re

from tests.test_security.test_security_migration import _migration_text, policy_names


def test_policy_names_are_stable_and_unique():
    names = policy_names()

    assert names
    assert all(name.startswith("rls_") for name in names)
    assert len(names) == len(set(names))


def test_resident_ticket_policy_references_active_membership_ownership():
    policy = _policy("rls_tickets_resident_select_owned_pending_identity")

    assert "user_unit_memberships membership" in policy
    assert "membership.unit_id = tickets.unit_id" in policy
    assert "membership.is_active = true" in policy
    assert "false" in policy


def test_technician_ticket_policy_references_active_assignment():
    policy = _policy("rls_tickets_technician_select_assigned_pending_identity")

    assert "ticket_assignments assignment" in policy
    assert "assignment.ticket_id = tickets.id" in policy
    assert "assignment.is_active = true" in policy
    assert "false" in policy


def test_notification_policy_references_recipient_ownership():
    policy = _policy("rls_notifications_user_select_owned_pending_identity")

    assert "recipient_user_id = NULL::uuid" in policy
    assert "false" in policy


def test_audit_policies_deny_unsafe_client_mutation():
    text = _migration_text()

    assert "rls_audit_logs_deny_client_update" in text
    assert "FOR UPDATE" in text
    assert "rls_audit_logs_deny_client_delete" in text
    assert "FOR DELETE" in text
    assert "USING (false)" in text


def test_no_supabase_identity_functions_are_used_without_confirmation():
    text = _migration_text()

    assert "auth.uid()" not in text
    assert "auth.jwt()" not in text


def _policy(name: str) -> str:
    text = _migration_text()
    match = re.search(rf"CREATE POLICY {name}.*?(?=\"\"\"\)|op\.execute\()", text, flags=re.DOTALL)
    if not match:
        raise AssertionError(f"Policy not found: {name}")
    return match.group(0)
