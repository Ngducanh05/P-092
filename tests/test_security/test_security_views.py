"""Static tests for database security views."""

from tests.test_security.test_security_migration import _migration_text

RESTRICTED_COLUMNS = {
    "severity_score",
    "red_flag_score",
    "impact_score",
    "density_score",
    "age_score",
    "total_score",
    "scoring_reasons",
    "confidence",
    "model_name",
    "audit_metadata",
    "old_values",
    "new_values",
}


def test_security_views_are_created_with_security_invoker():
    text = _migration_text()

    assert "CREATE VIEW resident_ticket_view" in text
    assert "CREATE VIEW technician_ticket_view" in text
    assert "WITH (security_invoker = true)" in text


def test_security_views_exclude_internal_scoring_and_audit_fields():
    text = _migration_text()
    resident_view = _view_sql(text, "resident_ticket_view")
    technician_view = _view_sql(text, "technician_ticket_view")

    for column_name in RESTRICTED_COLUMNS:
        assert column_name not in resident_view
        assert column_name not in technician_view


def test_coordinator_view_not_created_without_scope():
    assert "coordinator_ticket_view" not in _migration_text()


def _view_sql(text: str, view_name: str) -> str:
    start = text.index(f"CREATE VIEW {view_name}")
    next_execute = text.find('"""\n    )', start)
    return text[start:next_execute]
