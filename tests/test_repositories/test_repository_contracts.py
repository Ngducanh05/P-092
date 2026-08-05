"""Repository contract tests."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_ticket_repository_exposes_scoped_methods_only():
    text = (PROJECT_ROOT / "src" / "repositories" / "ticket_repository.py").read_text(encoding="utf-8")

    assert "list_resident_accessible_tickets" in text
    assert "get_resident_accessible_ticket" in text
    assert "list_coordinator_tickets" in text
    assert "get_ticket_by_id_for_coordinator" in text
    assert "def list_all" not in text
    assert "def get_any" not in text


def test_unit_repository_uses_active_membership_predicates():
    text = (PROJECT_ROOT / "src" / "repositories" / "unit_repository.py").read_text(encoding="utf-8")

    assert "UserUnitMembership.is_active.is_(True)" in text
    assert "Unit.is_active.is_(True)" in text
