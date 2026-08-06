"""Metadata tests for final operational database models."""

import inspect as python_inspect

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from src.database.base import Base
from src.database.models import (
    AuditLog,
    Notification,
    ResidentUnitMembership,
    TicketAttachmentUploadSession,
    TicketStatusHistory,
)
from src.models.enums import TicketStatus

OPERATIONAL_TABLES = {
    "resident_unit_memberships",
    "ticket_attachment_upload_sessions",
    "ticket_status_history",
    "notifications",
    "audit_logs",
}
FORBIDDEN_COLUMN_TERMS = ("password", "access_token", "token", "otp", "secret")


def test_operational_models_import_successfully():
    assert ResidentUnitMembership.__tablename__ == "resident_unit_memberships"
    assert TicketAttachmentUploadSession.__tablename__ == "ticket_attachment_upload_sessions"
    assert TicketStatusHistory.__tablename__ == "ticket_status_history"
    assert Notification.__tablename__ == "notifications"
    assert AuditLog.__tablename__ == "audit_logs"


def test_operational_tables_registered_in_metadata():
    assert OPERATIONAL_TABLES <= set(Base.metadata.tables)
    assert "user_unit_memberships" not in Base.metadata.tables
    assert "ticket_assignments" not in Base.metadata.tables


def test_every_operational_table_has_primary_key():
    for table_name in OPERATIONAL_TABLES:
        assert Base.metadata.tables[table_name].primary_key.columns


def test_operational_foreign_keys_point_to_expected_tables():
    expected = {
        ("resident_unit_memberships", "resident_id", "residents.id", "RESTRICT"),
        ("resident_unit_memberships", "unit_id", "units.id", "RESTRICT"),
        ("ticket_attachment_upload_sessions", "resident_id", "residents.id", "RESTRICT"),
        ("ticket_status_history", "ticket_id", "tickets.id", "CASCADE"),
        ("notifications", "ticket_id", "tickets.id", "SET NULL"),
    }
    actual = {
        (table.name, foreign_key.parent.name, foreign_key.target_fullname, foreign_key.ondelete)
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
    }

    assert expected <= actual


def test_shared_enums_are_reused_by_operational_tables():
    status_history = Base.metadata.tables["ticket_status_history"]

    assert status_history.c.from_status.type.enum_class is TicketStatus
    assert status_history.c.to_status.type.enum_class is TicketStatus
    assert status_history.c.to_status.type.name == "ticket_status_enum"


def test_no_duplicate_enum_classes_declared_inside_operational_models():
    import src.database.models.audit_log as audit_log_module
    import src.database.models.notification as notification_module
    import src.database.models.resident_unit_membership as resident_unit_membership_module
    import src.database.models.ticket_status_history as ticket_status_history_module

    allowed = {TicketStatus}
    for module in (
        audit_log_module,
        notification_module,
        resident_unit_membership_module,
        ticket_status_history_module,
    ):
        declared_enums = [
            member
            for member in vars(module).values()
            if python_inspect.isclass(member) and issubclass(member, tuple(allowed)) and member not in allowed
        ]
        assert declared_enums == []


def test_unique_constraints_for_memberships():
    assert _unique_column_sets("resident_unit_memberships") >= {("resident_id", "unit_id")}


def test_status_history_uses_ticket_status_enum():
    table = Base.metadata.tables["ticket_status_history"]

    assert isinstance(table.c.from_status.type, SQLEnum)
    assert isinstance(table.c.to_status.type, SQLEnum)
    assert table.c.to_status.type.enum_class is TicketStatus


def test_shared_auth_identity_columns_are_scalar_uuids_for_sqlite_compatibility():
    assert Base.metadata.tables["ticket_status_history"].c.changed_by_auth_user_id.nullable is True
    assert Base.metadata.tables["notifications"].c.recipient_auth_user_id.nullable is False
    assert Base.metadata.tables["audit_logs"].c.actor_auth_user_id.nullable is True


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
