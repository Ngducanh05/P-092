"""Tests for required Step 6-8 database security documentation."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs" / "database"
REQUIRED_DOCS = {
    "authorization-context-analysis.md",
    "data-ownership-matrix.md",
    "access-control-matrix.md",
    "rls-policy-design.md",
    "security-views.md",
    "attachment-security.md",
    "data-leakage-risk-matrix.md",
    "audit-policy.md",
    "retention-and-deletion-policy.md",
    "index-and-query-review.md",
    "data-dictionary.md",
    "backend-database-contract.md",
    "migration-guide.md",
    "final-database-report.md",
}
ACTORS = ("RESIDENT", "BQL", "SYSTEM / AI", "SERVICE ROLE", "ANONYMOUS")
RISKS = (
    "unit_id",
    "unassigned UUID",
    "notification",
    "scoring breakdown",
    "Public attachment",
    "Service-role key",
    "Secrets written to audit",
    "Excessive PII",
    "AI receives",
    "SQL injection",
    "IDOR",
    "BQL system-wide MVP read",
    "View owner",
    "Deactivated users",
    "Unlinked membership",
    "RLS denies service",
    "Service role bypasses",
    "Migration runs on production",
    "Test data contains real PII",
)


def test_required_security_documentation_files_exist():
    for filename in REQUIRED_DOCS:
        assert (DOCS_DIR / filename).is_file()


def test_access_matrix_covers_all_required_actors():
    text = (DOCS_DIR / "access-control-matrix.md").read_text(encoding="utf-8")

    for actor in ACTORS:
        assert actor in text


def test_risk_matrix_includes_required_scenarios():
    text = (DOCS_DIR / "data-leakage-risk-matrix.md").read_text(encoding="utf-8")

    for risk in RISKS:
        assert risk in text


def test_final_report_marks_live_postgresql_not_tested():
    text = (DOCS_DIR / "final-database-report.md").read_text(encoding="utf-8")

    assert "NOT TESTED ON LIVE POSTGRESQL" in text
    assert "Legacy ticket status values" in text
