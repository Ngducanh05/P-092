"""Static tests for final database security views."""

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


def test_resident_security_view_is_created_with_security_invoker():
    text = _migration_text()

    assert "CREATE VIEW resident_ticket_view" in text
    assert "WITH (security_invoker = true)" in text


def test_technician_security_view_is_removed():
    text = _migration_text()

    assert "DROP VIEW IF EXISTS public.technician_ticket_view" in text
    assert "CREATE VIEW technician_ticket_view" not in text


def test_security_view_excludes_internal_scoring_and_audit_fields():
    resident_view = _view_sql(_migration_text(), "resident_ticket_view")

    for column_name in RESTRICTED_COLUMNS:
        assert column_name not in resident_view


def _view_sql(text: str, view_name: str) -> str:
    start = text.index(f"CREATE VIEW {view_name}")
    next_execute = text.find("CREATE POLICY", start)
    return text[start:next_execute]
