"""Tests for Technician assignment transition service logic."""

from uuid import uuid4

import pytest

from src.database.models.resident import Resident
from src.database.models.technician_profile import TechnicianProfile
from src.database.models.ticket import Ticket
from src.database.models.ticket_assignment import TicketAssignment
from src.database.models.unit import Unit
from src.models.api.errors import (
    ASSIGNMENT_NOT_FOUND,
    COMPLETION_EVIDENCE_REQUIRED,
    INVALID_ASSIGNMENT_TRANSITION,
    UNABLE_REASON_REQUIRED,
    DomainError,
)
from src.models.enums import AssignmentStatus, Category, Priority, TicketStatus
from src.services.assignment_service import AssignmentService


def _setup(db):
    unit = Unit(id=uuid4(), building_code="A", floor="1", unit_number="101", is_active=True)
    resident = Resident(id=uuid4(), phone_number=f"+8490{uuid4().int % 10_000_000:07d}", is_active=True)
    tech = TechnicianProfile(id=uuid4(), email=f"tech-{uuid4().hex}@example.com", is_active=True, is_available=True)
    db.add_all([unit, resident, tech])
    db.flush()
    ticket = Ticket(
        id=uuid4(),
        resident_id=resident.id,
        unit_id=unit.id,
        title="Test",
        description="Test description",
        status=TicketStatus.ASSIGNED,
        category=Category.WATER,
        priority=Priority.P2,
    )
    db.add(ticket)
    db.flush()
    assignment = TicketAssignment(
        ticket_id=ticket.id,
        technician_id=tech.id,
        assigned_by_auth_user_id=uuid4(),
        status=AssignmentStatus.ASSIGNED,
        is_active=True,
    )
    db.add(assignment)
    db.commit()
    return tech, ticket, assignment


class TestAcceptAssignment:
    def test_accept_transitions_to_accepted(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        result = AssignmentService(db_session).accept_assignment(assignment.id, tech.id)
        assert result.status == AssignmentStatus.ACCEPTED
        assert result.accepted_at is not None

    def test_accept_does_not_change_ticket_status(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        AssignmentService(db_session).accept_assignment(assignment.id, tech.id)
        db_session.refresh(ticket)
        assert ticket.status == TicketStatus.ASSIGNED

    def test_accept_wrong_technician_returns_not_found(self, db_session):
        _tech, _ticket, assignment = _setup(db_session)
        other_tech_id = uuid4()
        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).accept_assignment(assignment.id, other_tech_id)
        assert exc.value.code == ASSIGNMENT_NOT_FOUND

    def test_cannot_accept_already_accepted(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        AssignmentService(db_session).accept_assignment(assignment.id, tech.id)
        db_session.refresh(assignment)
        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).accept_assignment(assignment.id, tech.id)
        assert exc.value.code == INVALID_ASSIGNMENT_TRANSITION


class TestInProgressTransition:
    def test_accepted_to_in_progress(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        svc = AssignmentService(db_session)
        svc.accept_assignment(assignment.id, tech.id)
        db_session.refresh(assignment)
        result = svc.update_assignment_status(assignment.id, tech.id, AssignmentStatus.IN_PROGRESS, None)
        assert result.status == AssignmentStatus.IN_PROGRESS
        assert result.started_at is not None

    def test_in_progress_updates_ticket_status(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        svc = AssignmentService(db_session)
        svc.accept_assignment(assignment.id, tech.id)
        db_session.refresh(assignment)
        svc.update_assignment_status(assignment.id, tech.id, AssignmentStatus.IN_PROGRESS, None)
        db_session.refresh(ticket)
        assert ticket.status == TicketStatus.IN_PROGRESS

    def test_in_progress_records_work_note_and_notifies_resident(self, db_session):
        from src.database.models.notification import Notification

        tech, ticket, assignment = _setup(db_session)
        service = AssignmentService(db_session)
        service.accept_assignment(assignment.id, tech.id)
        result = service.update_assignment_status(
            assignment.id,
            tech.id,
            AssignmentStatus.IN_PROGRESS,
            None,
            work_note="  Replaced damaged valve  ",
        )

        assert result.work_note == "Replaced damaged valve"
        notification = db_session.query(Notification).filter_by(
            recipient_auth_user_id=ticket.resident_id,
            event_type="ticket_in_progress",
        ).one()
        assert notification.ticket_id == ticket.id

    def test_cannot_skip_directly_assigned_to_in_progress(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).update_assignment_status(
                assignment.id, tech.id, AssignmentStatus.IN_PROGRESS, None
            )
        assert exc.value.code == INVALID_ASSIGNMENT_TRANSITION


class TestUnableToHandleTransition:
    def test_assigned_to_unable(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        result = AssignmentService(db_session).update_assignment_status(
            assignment.id, tech.id, AssignmentStatus.UNABLE_TO_HANDLE, "Equipment missing"
        )
        assert result.status == AssignmentStatus.UNABLE_TO_HANDLE
        assert result.is_active is False
        assert result.ended_at is not None

    def test_unable_returns_ticket_to_waiting_assignment(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        AssignmentService(db_session).update_assignment_status(
            assignment.id, tech.id, AssignmentStatus.UNABLE_TO_HANDLE, "Equipment missing"
        )
        db_session.refresh(ticket)
        assert ticket.status == TicketStatus.WAITING_ASSIGNMENT

    def test_unable_requires_nonempty_reason(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).update_assignment_status(
                assignment.id, tech.id, AssignmentStatus.UNABLE_TO_HANDLE, ""
            )
        assert exc.value.code == UNABLE_REASON_REQUIRED

    def test_unable_reason_whitespace_raises(self, db_session):
        tech, _ticket, assignment = _setup(db_session)
        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).update_assignment_status(
                assignment.id, tech.id, AssignmentStatus.UNABLE_TO_HANDLE, "   "
            )
        assert exc.value.code == UNABLE_REASON_REQUIRED

    def test_unable_reason_none_raises(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).update_assignment_status(
                assignment.id, tech.id, AssignmentStatus.UNABLE_TO_HANDLE, None
            )
        assert exc.value.code == UNABLE_REASON_REQUIRED

    def test_accepted_to_unable(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        svc = AssignmentService(db_session)
        svc.accept_assignment(assignment.id, tech.id)
        db_session.refresh(assignment)
        result = svc.update_assignment_status(
            assignment.id, tech.id, AssignmentStatus.UNABLE_TO_HANDLE, "Reason"
        )
        assert result.status == AssignmentStatus.UNABLE_TO_HANDLE


class TestCompletedRejected:
    def test_completed_status_raises_evidence_required(self, db_session):
        tech, ticket, assignment = _setup(db_session)
        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).update_assignment_status(
                assignment.id, tech.id, AssignmentStatus.COMPLETED, None
            )
        assert exc.value.code == COMPLETION_EVIDENCE_REQUIRED


    def test_completed_for_another_technician_is_masked_as_not_found(self, db_session):
        _tech, _ticket, assignment = _setup(db_session)
        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).update_assignment_status(
                assignment.id, uuid4(), AssignmentStatus.COMPLETED, None
            )
        assert exc.value.code == ASSIGNMENT_NOT_FOUND


class TestTechnicianOwnershipEnforcement:
    def test_list_only_returns_own_assignments(self, db_session):
        tech1, ticket1, assignment1 = _setup(db_session)
        tech2, ticket2, assignment2 = _setup(db_session)
        svc = AssignmentService(db_session)
        result = svc.list_own_assignments(tech1.id)
        ids = {a.id for a in result}
        assert assignment1.id in ids
        assert assignment2.id not in ids

    def test_detail_other_technician_returns_not_found(self, db_session):
        tech1, _ticket, assignment = _setup(db_session)
        tech2, _ticket2, _assignment2 = _setup(db_session)
        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).get_own_assignment(assignment.id, tech2.id)
        assert exc.value.code == ASSIGNMENT_NOT_FOUND


def test_assignment_list_is_sorted_p3_then_p2_then_p1(db_session):
    tech, ticket_p2, assignment_p2 = _setup(db_session)
    unit = ticket_p2.unit
    resident = ticket_p2.resident

    def add(priority):
        ticket = Ticket(
            id=uuid4(),
            resident_id=resident.id,
            unit_id=unit.id,
            title=f"Ticket {priority.value}",
            description="Description",
            status=TicketStatus.ASSIGNED,
            category=Category.WATER,
            priority=priority,
        )
        db_session.add(ticket)
        db_session.flush()
        assignment = TicketAssignment(
            ticket_id=ticket.id,
            technician_id=tech.id,
            assigned_by_auth_user_id=uuid4(),
            status=AssignmentStatus.ASSIGNED,
            is_active=True,
        )
        db_session.add(assignment)
        return assignment

    assignment_p1 = add(Priority.P1)
    assignment_p3 = add(Priority.P3)
    db_session.commit()

    result = AssignmentService(db_session).list_own_assignments(tech.id)
    assert [item.id for item in result] == [assignment_p3.id, assignment_p2.id, assignment_p1.id]
