"""Tests for BQL assignment service logic (SQLite in-memory)."""

from uuid import uuid4

import pytest

from src.database.models.bql_staff import BQLStaff
from src.database.models.technician_profile import TechnicianProfile
from src.database.models.technician_skill import TechnicianSkill
from src.database.models.ticket import Ticket
from src.models.api.errors import (
    ASSIGNMENT_CONFLICT,
    TECHNICIAN_NOT_FOUND,
    TECHNICIAN_UNAVAILABLE,
    TICKET_NOT_FOUND,
    TICKET_NOT_READY_FOR_ASSIGNMENT,
    DomainError,
)
from src.models.enums import AssignmentStatus, Category, Priority, TicketStatus
from src.services.assignment_service import AssignmentService


def _make_bql(db) -> BQLStaff:
    bql = BQLStaff(id=uuid4(), email="bql@example.com", is_active=True)
    db.add(bql)
    db.commit()
    return bql


def _make_technician(db, *, email="tech@example.com", is_active=True, is_available=True) -> TechnicianProfile:
    tech = TechnicianProfile(id=uuid4(), email=email, is_active=is_active, is_available=is_available)
    db.add(tech)
    db.commit()
    return tech


def _add_skill(db, technician: TechnicianProfile, category: Category) -> TechnicianSkill:
    skill = TechnicianSkill(technician_id=technician.id, category=category)
    db.add(skill)
    db.commit()
    return skill


def _make_ticket(db, *, status=TicketStatus.WAITING_ASSIGNMENT, category: Category | None = Category.WATER) -> Ticket:
    from src.database.models.resident import Resident
    from src.database.models.unit import Unit

    unit = Unit(id=uuid4(), building_code="A", floor="1", unit_number="101", is_active=True)
    resident = Resident(id=uuid4(), phone_number="+84901234567", is_active=True)
    db.add_all([unit, resident])
    db.flush()
    ticket = Ticket(
        id=uuid4(),
        resident_id=resident.id,
        unit_id=unit.id,
        title="Test ticket",
        description="Some description here",
        status=status,
        category=category,
        priority=Priority.P2,
    )
    db.add(ticket)
    db.commit()
    return ticket


class TestBQLTechnicianList:
    def test_list_returns_active_technicians(self, db_session):
        _make_technician(db_session, email="a@example.com")
        _make_technician(db_session, email="b@example.com")
        service = AssignmentService(db_session)
        technicians, total = service.list_technicians(1, 20)
        assert total == 2
        assert len(technicians) == 2

    def test_list_includes_skills(self, db_session):
        tech = _make_technician(db_session)
        _add_skill(db_session, tech, Category.WATER)
        service = AssignmentService(db_session)
        technicians, _ = service.list_technicians(1, 20)
        assert len(technicians[0].skills) == 1
        assert technicians[0].skills[0].category == Category.WATER


class TestBQLAssignTicket:
    def test_successful_assignment(self, db_session):
        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        _add_skill(db_session, tech, Category.WATER)
        ticket = _make_ticket(db_session)
        service = AssignmentService(db_session)
        assignment = service.assign_ticket(ticket.id, tech.id, bql.id, "Note")
        assert assignment.status == AssignmentStatus.ASSIGNED
        assert assignment.is_active is True
        assert assignment.assigned_by_auth_user_id == bql.id

    def test_ticket_status_updated_to_assigned(self, db_session):
        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        _add_skill(db_session, tech, Category.WATER)
        ticket = _make_ticket(db_session)
        service = AssignmentService(db_session)
        service.assign_ticket(ticket.id, tech.id, bql.id, None)
        db_session.refresh(ticket)
        assert ticket.status == TicketStatus.ASSIGNED

    def test_status_history_appended(self, db_session):
        from src.database.models.ticket_status_history import TicketStatusHistory

        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        _add_skill(db_session, tech, Category.WATER)
        ticket = _make_ticket(db_session)
        service = AssignmentService(db_session)
        service.assign_ticket(ticket.id, tech.id, bql.id, None)
        count = db_session.query(TicketStatusHistory).filter_by(ticket_id=ticket.id).count()
        assert count >= 1

    def test_notification_created_for_technician(self, db_session):
        from src.database.models.notification import Notification

        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        _add_skill(db_session, tech, Category.WATER)
        ticket = _make_ticket(db_session)
        service = AssignmentService(db_session)
        service.assign_ticket(ticket.id, tech.id, bql.id, None)
        notifs = db_session.query(Notification).filter_by(recipient_auth_user_id=tech.id).all()
        assert len(notifs) == 1
        assert notifs[0].event_type == "ticket_assigned"

    def test_resident_is_notified_when_technician_is_assigned(self, db_session):
        from src.database.models.notification import Notification

        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        _add_skill(db_session, tech, Category.WATER)
        ticket = _make_ticket(db_session)
        AssignmentService(db_session).assign_ticket(ticket.id, tech.id, bql.id, None)

        notification = db_session.query(Notification).filter_by(
            recipient_auth_user_id=ticket.resident_id,
            event_type="technician_assigned",
        ).one()
        assert notification.ticket_id == ticket.id

    def test_audit_log_created(self, db_session):
        from src.database.models.audit_log import AuditLog

        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        _add_skill(db_session, tech, Category.WATER)
        ticket = _make_ticket(db_session)
        service = AssignmentService(db_session)
        service.assign_ticket(ticket.id, tech.id, bql.id, None)
        logs = db_session.query(AuditLog).filter_by(action="assign").all()
        assert len(logs) == 1
        assert logs[0].actor_auth_user_id == bql.id

    def test_ticket_without_category_rejected(self, db_session):
        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        ticket = _make_ticket(db_session, category=None)
        service = AssignmentService(db_session)
        with pytest.raises(DomainError) as exc:
            service.assign_ticket(ticket.id, tech.id, bql.id, None)
        assert exc.value.code == TICKET_NOT_READY_FOR_ASSIGNMENT

    @pytest.mark.parametrize(
        "status",
        [TicketStatus.NEW, TicketStatus.ANALYZING, TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED],
    )
    def test_ticket_not_waiting_assignment_is_rejected(self, db_session, status):
        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        _add_skill(db_session, tech, Category.WATER)
        ticket = _make_ticket(db_session, status=status)

        with pytest.raises(DomainError) as exc:
            AssignmentService(db_session).assign_ticket(ticket.id, tech.id, bql.id, None)

        assert exc.value.code == TICKET_NOT_READY_FOR_ASSIGNMENT

    def test_unknown_ticket_raises_not_found(self, db_session):
        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        service = AssignmentService(db_session)
        with pytest.raises(DomainError) as exc:
            service.assign_ticket(uuid4(), tech.id, bql.id, None)
        assert exc.value.code == TICKET_NOT_FOUND

    def test_unknown_technician_raises_not_found(self, db_session):
        bql = _make_bql(db_session)
        ticket = _make_ticket(db_session)
        service = AssignmentService(db_session)
        with pytest.raises(DomainError) as exc:
            service.assign_ticket(ticket.id, uuid4(), bql.id, None)
        assert exc.value.code == TECHNICIAN_NOT_FOUND

    def test_inactive_technician_rejected(self, db_session):
        bql = _make_bql(db_session)
        tech = _make_technician(db_session, is_active=False)
        ticket = _make_ticket(db_session)
        service = AssignmentService(db_session)
        with pytest.raises(DomainError) as exc:
            service.assign_ticket(ticket.id, tech.id, bql.id, None)
        assert exc.value.code == TECHNICIAN_UNAVAILABLE

    def test_unavailable_technician_rejected(self, db_session):
        bql = _make_bql(db_session)
        tech = _make_technician(db_session, is_available=False)
        ticket = _make_ticket(db_session)
        service = AssignmentService(db_session)
        with pytest.raises(DomainError) as exc:
            service.assign_ticket(ticket.id, tech.id, bql.id, None)
        assert exc.value.code == TECHNICIAN_UNAVAILABLE

    def test_missing_skill_rejected(self, db_session):
        bql = _make_bql(db_session)
        tech = _make_technician(db_session)
        # Add electricity skill, ticket needs water
        _add_skill(db_session, tech, Category.ELECTRICITY)
        ticket = _make_ticket(db_session, category=Category.WATER)
        service = AssignmentService(db_session)
        with pytest.raises(DomainError) as exc:
            service.assign_ticket(ticket.id, tech.id, bql.id, None)
        assert exc.value.code == TECHNICIAN_UNAVAILABLE

    def test_duplicate_active_assignment_rejected(self, db_session):
        bql = _make_bql(db_session)
        tech1 = _make_technician(db_session, email="t1@example.com")
        tech2 = _make_technician(db_session, email="t2@example.com")
        _add_skill(db_session, tech1, Category.WATER)
        _add_skill(db_session, tech2, Category.WATER)
        ticket = _make_ticket(db_session)
        service = AssignmentService(db_session)
        service.assign_ticket(ticket.id, tech1.id, bql.id, None)
        with pytest.raises(DomainError) as exc:
            service.assign_ticket(ticket.id, tech2.id, bql.id, None)
        assert exc.value.code == ASSIGNMENT_CONFLICT
