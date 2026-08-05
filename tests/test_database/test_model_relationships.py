"""Relationship tests for database ORM models."""

from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipDirection

from src.database.models import AIAnalysisRun, Ticket, TicketAttachment, TicketScoringResult, Unit, User


def test_relationships_have_matching_back_populates():
    expected = {
        User: {"tickets": "resident"},
        Unit: {"tickets": "unit"},
        Ticket: {
            "resident": "tickets",
            "unit": "tickets",
            "attachments": "ticket",
            "ai_analysis_runs": "ticket",
            "scoring_results": "ticket",
        },
        TicketAttachment: {"ticket": "attachments"},
        AIAnalysisRun: {"ticket": "ai_analysis_runs", "scoring_results": "ai_analysis_run"},
        TicketScoringResult: {"ticket": "scoring_results", "ai_analysis_run": "scoring_results"},
    }

    for model, relationships in expected.items():
        mapper_relationships = inspect(model).relationships
        for relationship_name, back_populates in relationships.items():
            assert mapper_relationships[relationship_name].back_populates == back_populates


def test_relationship_directions_and_collection_behavior():
    assert _relationship(User, "tickets").direction is RelationshipDirection.ONETOMANY
    assert _relationship(User, "tickets").uselist is True
    assert _relationship(Unit, "tickets").direction is RelationshipDirection.ONETOMANY
    assert _relationship(Unit, "tickets").uselist is True

    assert _relationship(Ticket, "resident").direction is RelationshipDirection.MANYTOONE
    assert _relationship(Ticket, "resident").uselist is False
    assert _relationship(Ticket, "unit").direction is RelationshipDirection.MANYTOONE
    assert _relationship(Ticket, "unit").uselist is False

    assert _relationship(Ticket, "attachments").direction is RelationshipDirection.ONETOMANY
    assert _relationship(Ticket, "attachments").uselist is True
    assert _relationship(Ticket, "ai_analysis_runs").direction is RelationshipDirection.ONETOMANY
    assert _relationship(Ticket, "ai_analysis_runs").uselist is True
    assert _relationship(Ticket, "scoring_results").direction is RelationshipDirection.ONETOMANY
    assert _relationship(Ticket, "scoring_results").uselist is True

    assert _relationship(TicketAttachment, "ticket").direction is RelationshipDirection.MANYTOONE
    assert _relationship(TicketAttachment, "ticket").uselist is False
    assert _relationship(AIAnalysisRun, "ticket").direction is RelationshipDirection.MANYTOONE
    assert _relationship(AIAnalysisRun, "ticket").uselist is False
    assert _relationship(AIAnalysisRun, "scoring_results").direction is RelationshipDirection.ONETOMANY
    assert _relationship(AIAnalysisRun, "scoring_results").uselist is True
    assert _relationship(TicketScoringResult, "ticket").direction is RelationshipDirection.MANYTOONE
    assert _relationship(TicketScoringResult, "ticket").uselist is False
    assert _relationship(TicketScoringResult, "ai_analysis_run").direction is RelationshipDirection.MANYTOONE
    assert _relationship(TicketScoringResult, "ai_analysis_run").uselist is False


def test_ticket_owned_child_relationships_use_delete_orphan_cascade():
    for relationship_name in ("attachments", "ai_analysis_runs", "scoring_results"):
        cascade = _relationship(Ticket, relationship_name).cascade
        assert "delete" in cascade
        assert "delete-orphan" in cascade


def test_user_and_unit_do_not_cascade_delete_tickets():
    assert "delete" not in _relationship(User, "tickets").cascade
    assert "delete-orphan" not in _relationship(User, "tickets").cascade
    assert "delete" not in _relationship(Unit, "tickets").cascade
    assert "delete-orphan" not in _relationship(Unit, "tickets").cascade


def _relationship(model: type[object], name: str):
    return inspect(model).relationships[name]
