"""Metadata tests for database ORM models."""

import inspect as python_inspect

from sqlalchemy import CheckConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB

from src.database.base import Base
from src.database.models import AIAnalysisRun, Ticket, TicketAttachmentUploadSession, TicketScoringResult
from src.models.enums import Category, Priority, Role, Severity, TicketStatus

EXPECTED_TABLES = {
    "users",
    "units",
    "tickets",
    "ticket_attachments",
    "ticket_attachment_upload_sessions",
    "ai_analysis_runs",
    "ticket_scoring_results",
}


def test_all_orm_models_import_successfully():
    from src.database.models import TicketAttachment, Unit, User

    assert User.__tablename__ == "users"
    assert Unit.__tablename__ == "units"
    assert Ticket.__tablename__ == "tickets"
    assert TicketAttachment.__tablename__ == "ticket_attachments"
    assert TicketAttachmentUploadSession.__tablename__ == "ticket_attachment_upload_sessions"
    assert AIAnalysisRun.__tablename__ == "ai_analysis_runs"
    assert TicketScoringResult.__tablename__ == "ticket_scoring_results"


def test_expected_tables_registered_in_metadata():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_every_expected_table_has_primary_key():
    for table_name in EXPECTED_TABLES:
        assert Base.metadata.tables[table_name].primary_key.columns


def test_expected_foreign_keys_exist():
    expected = {
        ("tickets", "resident_id", "users.id", "RESTRICT"),
        ("tickets", "unit_id", "units.id", "RESTRICT"),
        ("ticket_attachments", "ticket_id", "tickets.id", "CASCADE"),
        ("ticket_attachment_upload_sessions", "owner_user_id", "users.id", "RESTRICT"),
        ("ai_analysis_runs", "ticket_id", "tickets.id", "CASCADE"),
        ("ticket_scoring_results", "ticket_id", "tickets.id", "CASCADE"),
        ("ticket_scoring_results", "ai_analysis_run_id", "ai_analysis_runs.id", "SET NULL"),
    }
    actual = set()

    for table in Base.metadata.tables.values():
        for foreign_key in table.foreign_keys:
            actual.add(
                (
                    table.name,
                    foreign_key.parent.name,
                    foreign_key.target_fullname,
                    foreign_key.ondelete,
                )
            )

    assert expected <= actual


def test_users_contact_columns_support_supabase_auth_profiles():
    users = Base.metadata.tables["users"]
    index_names = {index.name for index in users.indexes}
    constraints = _check_constraints("users")

    assert users.c.id.default is None
    assert users.c.email.nullable is True
    assert users.c.phone_number.nullable is True
    assert users.c.full_name.nullable is True
    assert "ix_users_email_not_null" in index_names
    assert "ix_users_phone_number_not_null" in index_names
    assert "ck_users_email_or_phone" in constraints
    assert "ck_users_phone_number_e164" in constraints


def test_tickets_description_is_required():
    description = Base.metadata.tables["tickets"].c.description

    assert description.nullable is False


def test_ticket_enum_columns_use_shared_enum_classes():
    tickets = Base.metadata.tables["tickets"]

    assert tickets.c.status.type.enum_class is TicketStatus
    assert tickets.c.category.type.enum_class is Category
    assert tickets.c.severity.type.enum_class is Severity
    assert tickets.c.priority.type.enum_class is Priority


def test_stable_sql_enum_names_are_present():
    enum_names = {
        column.type.name
        for table in Base.metadata.tables.values()
        for column in table.c
        if isinstance(column.type, SQLEnum)
    }

    assert {"role_enum", "ticket_status_enum", "category_enum", "severity_enum", "priority_enum"} <= enum_names


def test_user_role_enum_uses_shared_role_class():
    users = Base.metadata.tables["users"]

    assert users.c.role.type.enum_class is Role


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
    import src.database.models.scoring_result as scoring_result_module
    import src.database.models.ticket as ticket_module
    import src.database.models.unit as unit_module
    import src.database.models.user as user_module

    allowed = {Category, Priority, Role, Severity, TicketStatus}
    for module in (
        ai_analysis_module,
        attachment_module,
        scoring_result_module,
        ticket_module,
        unit_module,
        user_module,
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
