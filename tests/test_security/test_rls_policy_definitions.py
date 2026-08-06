"""Static tests for final RLS policy definitions."""

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
    assert "membership.resident_id = (select auth.uid())" in policy
    assert "membership.is_active = true" in policy


def test_bql_ticket_policy_references_active_bql_staff():
    policy = _policy("rls_tickets_bql_select_all_mvp")

    assert "FROM bql_staff" in policy
    assert "bql_staff.id = (select auth.uid())" in policy
    assert "bql_staff.is_active = true" in policy


def test_notification_policy_references_recipient_auth_ownership():
    policy = _policy("rls_notifications_recipient_auth_select_owned")

    assert "recipient_auth_user_id = (select auth.uid())" in policy


def test_no_technician_policy_or_role_lookup_remains():
    text = _migration_text()

    assert "CREATE POLICY rls_tickets_technician" not in text
    assert "app_user.role" not in text


def _policy(name: str) -> str:
    text = _migration_text()
    match = re.search(rf"CREATE POLICY {name}.*?(?=\"\"\"\)|;)", text, flags=re.DOTALL)
    if not match:
        raise AssertionError(f"Policy not found: {name}")
    return match.group(0)
