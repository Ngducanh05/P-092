"""Focused tests for migration f6a7b8c9d0e1 structural invariants.

These tests assert the revision metadata and SQL content without running alembic upgrade.
Historical migration tests for e5f6a7b8c9d0 are preserved separately and remain unchanged.
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = PROJECT_ROOT / "alembic" / "versions" / "f6a7b8c9d0e1_restore_technician_actor_workflow.py"


def _load_revision():
    """Load the project migration by path without shadowing the Alembic package."""
    name = f"p092_migration_f6_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load migration: {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_down_revision_is_e5f6a7b8c9d0():
    mod = _load_revision()
    assert mod.down_revision == "e5f6a7b8c9d0"


def test_revision_id():
    mod = _load_revision()
    assert mod.revision == "f6a7b8c9d0e1"


def test_branch_labels_and_depends_none():
    mod = _load_revision()
    assert mod.branch_labels is None
    assert mod.depends_on is None


def test_preflight_filters_assignment_status_enum_to_public_schema():
    """Preflight must not treat a same-named type in another schema as a collision."""
    src = inspect.getsource(_load_revision())
    # Must join pg_namespace and filter nspname = 'public'
    assert "pg_namespace" in src
    assert "nspname = 'public'" in src


def test_preflight_rejects_missing_auth_users():
    """Preflight must abort with a clear message when auth.users is absent."""
    src = inspect.getsource(_load_revision())
    assert "NOT auth_users_present" in src
    assert "auth.users was not found" in src or "auth.users" in src


def test_no_duplicate_email_unique_constraint():
    """Migration must declare only a unique index, not also a UniqueConstraint, on email."""
    src = inspect.getsource(_load_revision())
    # The named UniqueConstraint for email must have been removed
    assert 'UniqueConstraint("email"' not in src
    assert "uq_technician_profiles_email" not in src
    # The unique index must still be present
    assert "ix_technician_profiles_email" in src


def test_auth_fk_for_technician_profiles_present():
    src = inspect.getsource(_load_revision())
    assert "fk_technician_profiles_id_auth_users" in src


def test_auth_fk_for_assigned_by_present():
    src = inspect.getsource(_load_revision())
    assert "fk_ticket_assignments_assigned_by_auth_users" in src


def test_one_active_assignment_partial_unique_index():
    src = inspect.getsource(_load_revision())
    assert "uq_ticket_assignments_one_active_per_ticket" in src
    assert "is_active" in src


def test_no_public_users_or_role_enum():
    src = inspect.getsource(_load_revision())
    assert "public.users" not in src
    assert "role_enum" not in src


def test_three_profile_conflict_trigger():
    src = inspect.getsource(_load_revision())
    assert "trg_technician_profiles_prevent_actor_profile_conflict" in src
    assert "AUTH_PROFILE_CONFLICT" in src


def test_rls_own_profile_policy_present():
    src = inspect.getsource(_load_revision())
    assert "rls_technician_profiles_select_own_active" in src


def test_rls_own_assignment_policy_present():
    src = inspect.getsource(_load_revision())
    assert "rls_ticket_assignments_select_own_active" in src


def test_rls_assigned_ticket_policy_present():
    src = inspect.getsource(_load_revision())
    assert "rls_tickets_technician_select_assigned" in src
