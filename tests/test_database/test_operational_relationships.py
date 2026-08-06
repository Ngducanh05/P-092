"""Relationship tests for final operational database models."""

from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipDirection

from src.database.models import (
    AIAnalysisRun,
    Notification,
    Resident,
    ResidentUnitMembership,
    Ticket,
    TicketAttachmentUploadSession,
    TicketStatusHistory,
    Unit,
)


def test_operational_relationships_have_matching_back_populates():
    expected = {
        Resident: {
            "unit_memberships": "resident",
            "ticket_attachment_upload_sessions": "resident",
        },
        Unit: {"resident_memberships": "unit"},
        Ticket: {
            "status_history": "ticket",
            "notifications": "ticket",
        },
        ResidentUnitMembership: {"resident": "unit_memberships", "unit": "resident_memberships"},
        TicketAttachmentUploadSession: {"resident": "ticket_attachment_upload_sessions"},
        TicketStatusHistory: {"ticket": "status_history"},
        Notification: {"ticket": "notifications"},
    }

    for model, relationships in expected.items():
        mapper_relationships = inspect(model).relationships
        for relationship_name, back_populates in relationships.items():
            assert mapper_relationships[relationship_name].back_populates == back_populates


def test_ticket_status_history_preserves_history_as_collection():
    assert _relationship(Ticket, "status_history").direction is RelationshipDirection.ONETOMANY
    assert _relationship(Ticket, "status_history").uselist is True
    assert _relationship(TicketStatusHistory, "ticket").direction is RelationshipDirection.MANYTOONE


def test_resident_removal_does_not_cascade_operational_history():
    for relationship_name in ("unit_memberships", "ticket_attachment_upload_sessions"):
        cascade = _relationship(Resident, relationship_name).cascade
        assert "delete" not in cascade
        assert "delete-orphan" not in cascade


def test_ticket_owned_operational_children_can_cascade_only_with_ticket_delete():
    cascade = _relationship(Ticket, "status_history").cascade
    assert "delete" in cascade
    assert "delete-orphan" in cascade

    assert "delete" not in _relationship(Ticket, "notifications").cascade
    assert "delete-orphan" not in _relationship(Ticket, "notifications").cascade


def test_ai_analysis_relationships_preserved():
    assert _relationship(AIAnalysisRun, "scoring_results").back_populates == "ai_analysis_run"


def _relationship(model: type[object], name: str):
    return inspect(model).relationships[name]
