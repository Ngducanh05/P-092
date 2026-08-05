"""Index tests for Step 5 operational database models."""

import src.database.models  # noqa: F401
from src.database.base import Base


def test_required_operational_indexes_exist():
    expected = {
        ("user_unit_memberships", "ix_user_unit_memberships_user_active", ("user_id", "is_active"), False),
        ("user_unit_memberships", "ix_user_unit_memberships_unit_active", ("unit_id", "is_active"), False),
        ("technician_skills", "ix_technician_skills_category", ("category",), False),
        ("ticket_assignments", "ix_ticket_assignments_ticket_assigned_at", ("ticket_id", "assigned_at"), False),
        ("ticket_assignments", "ix_ticket_assignments_technician_active", ("technician_id", "is_active"), False),
        (
            "ticket_assignments",
            "uq_ticket_assignments_one_active_per_ticket",
            ("ticket_id",),
            True,
        ),
        ("ticket_status_history", "ix_ticket_status_history_ticket_created_at", ("ticket_id", "created_at"), False),
        (
            "notifications",
            "ix_notifications_recipient_unread_created_at",
            ("recipient_user_id", "is_read", "created_at"),
            False,
        ),
        ("notifications", "ix_notifications_ticket_id", ("ticket_id",), False),
        ("audit_logs", "ix_audit_logs_entity", ("entity_type", "entity_id"), False),
        ("audit_logs", "ix_audit_logs_actor_created_at", ("actor_user_id", "created_at"), False),
    }
    actual = {
        (table.name, index.name, tuple(column.name for column in index.columns), index.unique)
        for table in Base.metadata.tables.values()
        for index in table.indexes
    }

    assert expected <= actual


def test_ticket_has_at_most_one_active_assignment_index():
    index = _index("ticket_assignments", "uq_ticket_assignments_one_active_per_ticket")

    assert index.unique is True
    assert tuple(column.name for column in index.columns) == ("ticket_id",)
    assert str(index.dialect_options["postgresql"]["where"]) == "is_active"


def _index(table_name: str, index_name: str):
    table = Base.metadata.tables[table_name]
    return next(index for index in table.indexes if index.name == index_name)
