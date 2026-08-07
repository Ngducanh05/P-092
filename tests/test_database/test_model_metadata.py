"""Metadata tests for final database ORM models."""

import inspect as python_inspect

from sqlalchemy import CheckConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB

from src.database.base import Base
from src.database.models import (
    AIAnalysisRun,
    BQLStaff,
    Resident,
    Ticket,
    TicketAttachmentUploadSession,
    TicketScoringResult,
)
from src.models.enums import Category, Priority, Severity, TicketStatus

EXPECTED_TABLES = {
    "residents",
    "bql_staff",
    "technician_profiles",
    "technician_skills",
    "ticket_assignments",
    "resident_unit_memberships",
    "units",
    "tickets",
    "ticket_attachments",
    "ticket_attachment_upload_sessions",
    "ticket_status_history",
    "notifications",
    "audit_logs",
    "ai_analysis_runs",
    "ticket_scoring_results",
}
REMOVED_TABLES = {"users"}


def test_all_orm_models_import_successfully():
    from src.database.models import (
        AuditLog,
        Notification,
        ResidentUnitMembership,
        TicketAttachment,
        TicketStatusHistory,
        Unit,
    )

    assert Resident.__tablename__ == "residents"
    assert BQLStaff.__tablename__ == "bql_staff"
    assert ResidentUnitMembership.__tablename__ == "resident_unit_memberships"
    assert Unit.__tablename__ == "units"
    assert Ticket.__tablename__ == "tickets"
    assert TicketAttachment.__tablename__ == "ticket_attachments"
    assert TicketAttachmentUploadSession.__tablename__ == "ticket_attachment_upload_sessions"
    assert TicketStatusHistory.__tablename__ == "ticket_status_history"
    assert Notification.__tablename__ == "notifications"
    assert AuditLog.__tablename__ == "audit_logs"
    assert AIAnalysisRun.__tablename__ == "ai_analysis_runs"
    assert TicketScoringResult.__tablename__ == "ticket_scoring_results"


def test_expected_tables_registered_in_metadata():
    names = set(Base.metadata.tables)

    assert EXPECTED_TABLES <= names
    assert REMOVED_TABLES.isdisjoint(names)


def test_every_expected_table_has_primary_key():
    for table_name in EXPECTED_TABLES:
        assert Base.metadata.tables[table_name].primary_key.columns


def test_expected_foreign_keys_exist():
    expected = {
        ("resident_unit_memberships", "resident_id", "residents.id", "RESTRICT"),
        ("resident_unit_memberships", "unit_id", "units.id", "RESTRICT"),
        ("tickets", "resident_id", "residents.id", "RESTRICT"),
        ("tickets", "unit_id", "units.id", "RESTRICT"),
        ("ticket_attachments", "ticket_id", "tickets.id", "CASCADE"),
        ("ticket_attachment_upload_sessions", "resident_id", "residents.id", "RESTRICT"),
        ("ticket_status_history", "ticket_id", "tickets.id", "CASCADE"),
        ("notifications", "ticket_id", "tickets.id", "SET NULL"),
        ("ai_analysis_runs", "ticket_id", "tickets.id", "CASCADE"),
        ("ticket_scoring_results", "ticket_id", "tickets.id", "CASCADE"),
        ("ticket_scoring_results", "ai_analysis_run_id", "ai_analysis_runs.id", "SET NULL"),
    }
    actual = {
        (table.name, foreign_key.parent.name, foreign_key.target_fullname, foreign_key.ondelete)
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
    }

    assert expected <= actual


def test_profile_tables_support_supabase_auth_profiles():
    residents = Base.metadata.tables["residents"]
    bql_staff = Base.metadata.tables["bql_staff"]
    constraints = _check_constraints("residents")

    assert residents.c.id.default is None
    assert residents.c.phone_number.nullable is False
    assert residents.c.full_name.nullable is True
    assert bql_staff.c.id.default is None
    assert bql_staff.c.email.nullable is False
    assert bql_staff.c.full_name.nullable is True
    assert "ck_residents_phone_number_e164" in constraints


def test_tickets_description_is_required():
    description = Base.metadata.tables["tickets"].c.description

    assert description.nullable is False


def test_ticket_enum_columns_use_shared_enum_classes():
    tickets = Base.metadata.tables["tickets"]

    assert tickets.c.status.type.enum_class is TicketStatus
    assert tickets.c.category.type.enum_class is Category
    assert tickets.c.severity.type.enum_class is Severity
    assert tickets.c.priority.type.enum_class is Priority


def test_stable_sql_enum_names_are_present_without_role_enum():
    enum_names = {
        column.type.name
        for table in Base.metadata.tables.values()
        for column in table.c
        if isinstance(column.type, SQLEnum)
    }

    assert {"ticket_status_enum", "category_enum", "severity_enum", "priority_enum"} <= enum_names
    assert "role_enum" not in enum_names


def test_ai_analysis_confidence_range_constraint_exists():
    constraints = _check_constraints("ai_analysis_runs")

    assert "ck_ai_analysis_runs_confidence_range" in constraints
    assert "confidence >= 0 AND confidence <= 1" in constraints["ck_ai_analysis_runs_confidence_range"]


def test_scoring_constraints_exist():
    constraints = _check_constraints("ticket_scoring_results")

    expected_names = {
        "ck_ticket_scoring_severity_range",
        "ck_ticket_scoring_red_flag_range",
        "ck_ticket_scoring_impact_range",
        "ck_ticket_scoring_density_range",
        "ck_ticket_scoring_age_range",
        "ck_ticket_scoring_total_range",
        "ck_ticket_scoring_total_equals_components",
    }
    assert expected_names <= set(constraints)


def test_timestamp_columns_are_timezone_aware():
    for table_name in EXPECTED_TABLES:
        table = Base.metadata.tables[table_name]
        timestamp_columns = [column for column in table.c if column.name.endswith("_at")]
        assert timestamp_columns
        for column in timestamp_columns:
            assert column.type.timezone is True


def test_json_list_fields_use_postgresql_jsonb():
    ai_analysis = Base.metadata.tables["ai_analysis_runs"]
    scoring = Base.metadata.tables["ticket_scoring_results"]

    assert isinstance(ai_analysis.c.red_flags.type, JSONB)
    assert isinstance(ai_analysis.c.text_categories.type, JSONB)
    assert isinstance(scoring.c.scoring_reasons.type, JSONB)


def test_no_duplicate_enum_classes_declared_inside_database_models():
    import src.database.models.ai_analysis as ai_analysis_module
    import src.database.models.attachment as attachment_module
    import src.database.models.resident as resident_module
    import src.database.models.scoring_result as scoring_result_module
    import src.database.models.ticket as ticket_module
    import src.database.models.unit as unit_module

    allowed = {Category, Priority, Severity, TicketStatus}
    for module in (
        ai_analysis_module,
        attachment_module,
        scoring_result_module,
        resident_module,
        ticket_module,
        unit_module,
    ):
        declared_enums = [
            member
            for member in vars(module).values()
            if python_inspect.isclass(member) and issubclass(member, tuple(allowed)) and member not in allowed
        ]
        assert declared_enums == []


def _check_constraints(table_name: str) -> dict[str, str]:
    table = Base.metadata.tables[table_name]
    return {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
