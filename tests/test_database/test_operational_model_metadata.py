"""Metadata tests for Step 5 operational database models."""

import inspect as python_inspect

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from src.database.base import Base
from src.database.models import (
    AuditLog,
    Notification,
    TechnicianProfile,
    TechnicianSkill,
    TicketAssignment,
    TicketAttachmentUploadSession,
    TicketStatusHistory,
    UserUnitMembership,
)
from src.models.enums import Category, TicketStatus

OPERATIONAL_TABLES = {
    "user_unit_memberships",
    "technician_profiles",
    "technician_skills",
    "ticket_assignments",
    "ticket_attachment_upload_sessions",
    "ticket_status_history",
    "notifications",
    "audit_logs",
}
FORBIDDEN_COLUMN_TERMS = ("password", "access_token", "token", "otp", "secret")


def test_operational_models_import_successfully():
    assert UserUnitMembership.__tablename__ == "user_unit_memberships"
    assert TechnicianProfile.__tablename__ == "technician_profiles"
    assert TechnicianSkill.__tablename__ == "technician_skills"
    assert TicketAssignment.__tablename__ == "ticket_assignments"
    assert TicketAttachmentUploadSession.__tablename__ == "ticket_attachment_upload_sessions"
    assert TicketStatusHistory.__tablename__ == "ticket_status_history"
    assert Notification.__tablename__ == "notifications"
    assert AuditLog.__tablename__ == "audit_logs"


def test_operational_tables_registered_in_metadata():
    assert OPERATIONAL_TABLES <= set(Base.metadata.tables)


def test_every_operational_table_has_primary_key():
    for table_name in OPERATIONAL_TABLES:
        assert Base.metadata.tables[table_name].primary_key.columns


def test_operational_foreign_keys_point_to_expected_tables():
    expected = {
        ("user_unit_memberships", "user_id", "users.id", "RESTRICT"),
        ("user_unit_memberships", "unit_id", "units.id", "RESTRICT"),
        ("technician_profiles", "user_id", "users.id", "RESTRICT"),
        ("technician_skills", "technician_id", "technician_profiles.user_id", "RESTRICT"),
        ("ticket_assignments", "ticket_id", "tickets.id", "CASCADE"),
        ("ticket_assignments", "technician_id", "technician_profiles.user_id", "RESTRICT"),
        ("ticket_assignments", "assigned_by_user_id", "users.id", "RESTRICT"),
        ("ticket_attachment_upload_sessions", "owner_user_id", "users.id", "RESTRICT"),
        ("ticket_status_history", "ticket_id", "tickets.id", "CASCADE"),
        ("ticket_status_history", "changed_by_user_id", "users.id", "SET NULL"),
        ("notifications", "recipient_user_id", "users.id", "RESTRICT"),
        ("notifications", "ticket_id", "tickets.id", "SET NULL"),
        ("audit_logs", "actor_user_id", "users.id", "SET NULL"),
    }
    actual = {
        (table.name, foreign_key.parent.name, foreign_key.target_fullname, foreign_key.ondelete)
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
    }

    assert expected <= actual


def test_shared_enums_are_reused_by_operational_tables():
    technician_skills = Base.metadata.tables["technician_skills"]
    status_history = Base.metadata.tables["ticket_status_history"]

    assert technician_skills.c.category.type.enum_class is Category
    assert technician_skills.c.category.type.name == "category_enum"
    assert status_history.c.from_status.type.enum_class is TicketStatus
    assert status_history.c.to_status.type.enum_class is TicketStatus
    assert status_history.c.to_status.type.name == "ticket_status_enum"


def test_no_duplicate_enum_classes_declared_inside_operational_models():
    import src.database.models.audit_log as audit_log_module
    import src.database.models.notification as notification_module
    import src.database.models.technician_profile as technician_profile_module
    import src.database.models.technician_skill as technician_skill_module
    import src.database.models.ticket_assignment as ticket_assignment_module
    import src.database.models.ticket_status_history as ticket_status_history_module
    import src.database.models.user_unit_membership as user_unit_membership_module

    allowed = {Category, TicketStatus}
    for module in (
        audit_log_module,
        notification_module,
        technician_profile_module,
        technician_skill_module,
        ticket_assignment_module,
        ticket_status_history_module,
        user_unit_membership_module,
    ):
        declared_enums = [
            member
            for member in vars(module).values()
            if python_inspect.isclass(member) and issubclass(member, tuple(allowed)) and member not in allowed
        ]
        assert declared_enums == []


def test_unique_constraints_for_memberships_and_skills():
    assert _unique_column_sets("user_unit_memberships") >= {("user_id", "unit_id")}
    assert _unique_column_sets("technician_skills") >= {("technician_id", "category")}


def test_status_history_uses_ticket_status_enum():
    table = Base.metadata.tables["ticket_status_history"]

    assert isinstance(table.c.from_status.type, SQLEnum)
    assert isinstance(table.c.to_status.type, SQLEnum)
    assert table.c.to_status.type.enum_class is TicketStatus


def test_notification_ownership_points_to_recipient_user():
    recipient_fk = next(iter(Base.metadata.tables["notifications"].c.recipient_user_id.foreign_keys))

    assert recipient_fk.target_fullname == "users.id"
    assert recipient_fk.ondelete == "RESTRICT"


def test_audit_json_fields_use_postgresql_jsonb():
    audit_logs = Base.metadata.tables["audit_logs"]

    assert isinstance(audit_logs.c.old_values.type, JSONB)
    assert isinstance(audit_logs.c.new_values.type, JSONB)
    assert isinstance(audit_logs.c["metadata"].type, JSONB)


def test_operational_timestamp_columns_are_timezone_aware():
    for table_name in OPERATIONAL_TABLES:
        timestamp_columns = [column for column in Base.metadata.tables[table_name].c if column.name.endswith("_at")]
        assert timestamp_columns
        for column in timestamp_columns:
            assert column.type.timezone is True


def test_no_sensitive_secret_columns_are_introduced():
    for table_name in OPERATIONAL_TABLES:
        for column in Base.metadata.tables[table_name].c:
            assert not any(term in column.name.lower() for term in FORBIDDEN_COLUMN_TERMS)


def _unique_column_sets(table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in Base.metadata.tables[table_name].constraints
        if isinstance(constraint, UniqueConstraint)
    }
