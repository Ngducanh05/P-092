"""Relationship tests for Step 5 operational database models."""

from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipDirection

from src.database.models import (
    AIAnalysisRun,
    AuditLog,
    Notification,
    TechnicianProfile,
    TechnicianSkill,
    Ticket,
    TicketAssignment,
    TicketStatusHistory,
    Unit,
    User,
    UserUnitMembership,
)


def test_operational_relationships_have_matching_back_populates():
    expected = {
        User: {
            "unit_memberships": "user",
            "technician_profile": "user",
            "assigned_ticket_records": "technician",
            "coordinator_assignment_records": "assigned_by_user",
            "status_changes": "changed_by_user",
            "notifications": "recipient_user",
            "audit_logs": "actor_user",
        },
        Unit: {"user_memberships": "unit"},
        Ticket: {
            "assignments": "ticket",
            "status_history": "ticket",
            "notifications": "ticket",
        },
        UserUnitMembership: {"user": "unit_memberships", "unit": "user_memberships"},
        TechnicianProfile: {
            "user": "technician_profile",
            "skills": "technician",
            "assigned_ticket_records": "technician_profile",
        },
        TechnicianSkill: {"technician": "skills"},
        TicketAssignment: {
            "ticket": "assignments",
            "technician": "assigned_ticket_records",
            "technician_profile": "assigned_ticket_records",
            "assigned_by_user": "coordinator_assignment_records",
        },
        TicketStatusHistory: {"ticket": "status_history", "changed_by_user": "status_changes"},
        Notification: {"recipient_user": "notifications", "ticket": "notifications"},
        AuditLog: {"actor_user": "audit_logs"},
    }

    for model, relationships in expected.items():
        mapper_relationships = inspect(model).relationships
        for relationship_name, back_populates in relationships.items():
            assert mapper_relationships[relationship_name].back_populates == back_populates


def test_user_to_technician_profile_is_one_to_one():
    assert _relationship(User, "technician_profile").direction is RelationshipDirection.ONETOMANY
    assert _relationship(User, "technician_profile").uselist is False
    assert _relationship(TechnicianProfile, "user").direction is RelationshipDirection.MANYTOONE
    assert _relationship(TechnicianProfile, "user").uselist is False


def test_ticket_assignments_preserve_history_as_collection():
    assert _relationship(Ticket, "assignments").direction is RelationshipDirection.ONETOMANY
    assert _relationship(Ticket, "assignments").uselist is True
    assert _relationship(TicketAssignment, "ticket").direction is RelationshipDirection.MANYTOONE
    assert _relationship(TicketAssignment, "ticket").uselist is False


def test_ticket_status_history_preserves_history_as_collection():
    assert _relationship(Ticket, "status_history").direction is RelationshipDirection.ONETOMANY
    assert _relationship(Ticket, "status_history").uselist is True
    assert _relationship(TicketStatusHistory, "ticket").direction is RelationshipDirection.MANYTOONE


def test_user_and_unit_deletion_do_not_cascade_delete_tickets():
    assert "delete" not in _relationship(User, "tickets").cascade
    assert "delete-orphan" not in _relationship(User, "tickets").cascade
    assert "delete" not in _relationship(Unit, "tickets").cascade
    assert "delete-orphan" not in _relationship(Unit, "tickets").cascade


def test_user_removal_does_not_cascade_operational_history():
    relationship_names = (
        "unit_memberships",
        "assigned_ticket_records",
        "coordinator_assignment_records",
        "status_changes",
        "notifications",
        "audit_logs",
    )
    for relationship_name in relationship_names:
        cascade = _relationship(User, relationship_name).cascade
        assert "delete" not in cascade
        assert "delete-orphan" not in cascade


def test_ticket_owned_operational_children_can_cascade_only_with_ticket_delete():
    for relationship_name in ("attachments", "ai_analysis_runs", "scoring_results", "assignments", "status_history"):
        cascade = _relationship(Ticket, relationship_name).cascade
        assert "delete" in cascade
        assert "delete-orphan" in cascade

    assert "delete" not in _relationship(Ticket, "notifications").cascade
    assert "delete-orphan" not in _relationship(Ticket, "notifications").cascade


def test_ai_analysis_relationships_preserved():
    assert _relationship(AIAnalysisRun, "scoring_results").back_populates == "ai_analysis_run"


def _relationship(model: type[object], name: str):
    return inspect(model).relationships[name]
