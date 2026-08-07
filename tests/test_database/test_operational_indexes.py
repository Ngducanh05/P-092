"""Index tests for final operational database models."""

import src.database.models  # noqa: F401
from src.database.base import Base


def test_required_operational_indexes_exist():
    expected = {
        (
            "resident_unit_memberships",
            "ix_resident_unit_memberships_resident_active",
            ("resident_id", "is_active"),
            False,
        ),
        ("resident_unit_memberships", "ix_resident_unit_memberships_unit_active", ("unit_id", "is_active"), False),
        (
            "ticket_attachment_upload_sessions",
            "ix_ticket_attachment_upload_sessions_resident_status",
            ("resident_id", "status"),
            False,
        ),
        (
            "ticket_attachment_upload_sessions",
            "ix_ticket_attachment_upload_sessions_expires_at",
            ("expires_at",),
            False,
        ),
        ("ticket_status_history", "ix_ticket_status_history_ticket_created_at", ("ticket_id", "created_at"), False),
        (
            "notifications",
            "ix_notifications_recipient_auth_unread_created_at",
            ("recipient_auth_user_id", "is_read", "created_at"),
            False,
        ),
        ("notifications", "ix_notifications_ticket_id", ("ticket_id",), False),
        ("audit_logs", "ix_audit_logs_entity", ("entity_type", "entity_id"), False),
        ("audit_logs", "ix_audit_logs_actor_auth_created_at", ("actor_auth_user_id", "created_at"), False),
        ("technician_profiles", "ix_technician_profiles_email", ("email",), True),
        (
            "technician_profiles",
            "ix_technician_profiles_active_available",
            ("is_active", "is_available"),
            False,
        ),
        ("technician_skills", "ix_technician_skills_category", ("category",), False),
        ("technician_skills", "ix_technician_skills_technician_id", ("technician_id",), False),
        (
            "ticket_assignments",
            "ix_ticket_assignments_technician_active",
            ("technician_id", "is_active"),
            False,
        ),
        (
            "ticket_assignments",
            "ix_ticket_assignments_ticket_assigned_at",
            ("ticket_id", "assigned_at"),
            False,
        ),
        (
            "ticket_assignments",
            "uq_ticket_assignments_one_active_per_ticket",
            ("ticket_id",),
            True,
        ),
    }
    actual = {
        (table.name, index.name, tuple(column.name for column in index.columns), index.unique)
        for table in Base.metadata.tables.values()
        for index in table.indexes
    }

    assert expected <= actual
