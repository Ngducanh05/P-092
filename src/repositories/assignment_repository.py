"""Assignment and technician roster persistence operations."""

from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from src.database.models.technician_profile import TechnicianProfile
from src.database.models.technician_skill import TechnicianSkill
from src.database.models.ticket import Ticket
from src.database.models.ticket_assignment import TicketAssignment
from src.models.enums import AssignmentStatus, Category, Priority


class AssignmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # Technician roster                                                    #
    # ------------------------------------------------------------------ #

    def list_active_available_technicians(
        self,
        page: int,
        page_size: int,
    ) -> tuple[list[TechnicianProfile], int]:
        query = (
            select(TechnicianProfile)
            .where(TechnicianProfile.is_active.is_(True))
            .options(selectinload(TechnicianProfile.skills))
        )
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = list(
            self.db.scalars(
                query.order_by(TechnicianProfile.email.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, int(total)

    def get_technician_with_skills(self, technician_id: UUID) -> TechnicianProfile | None:
        return self.db.scalar(
            select(TechnicianProfile)
            .where(TechnicianProfile.id == technician_id)
            .options(selectinload(TechnicianProfile.skills))
        )

    # ------------------------------------------------------------------ #
    # Assignment queries                                                   #
    # ------------------------------------------------------------------ #

    def get_active_assignment_for_ticket(self, ticket_id: UUID) -> TicketAssignment | None:
        return self.db.scalar(
            select(TicketAssignment)
            .where(TicketAssignment.ticket_id == ticket_id, TicketAssignment.is_active.is_(True))
            .with_for_update()
        )

    def get_assignment_for_technician(
        self,
        assignment_id: UUID,
        technician_id: UUID,
        *,
        lock: bool = False,
    ) -> TicketAssignment | None:
        """Return an active assignment owned by this technician, optionally row-locked."""
        query = (
            select(TicketAssignment)
            .where(
                TicketAssignment.id == assignment_id,
                TicketAssignment.technician_id == technician_id,
                TicketAssignment.is_active.is_(True),
            )
            .options(selectinload(TicketAssignment.ticket).selectinload(Ticket.attachments))
        )
        if lock:
            query = query.with_for_update()
        return self.db.scalar(query)

    def list_active_assignments_for_technician(
        self, technician_id: UUID
    ) -> list[TicketAssignment]:
        """List active assignments sorted by ticket priority then assigned_at."""
        priority_order = case(
            (Ticket.priority == Priority.P3, 1),
            (Ticket.priority == Priority.P2, 2),
            (Ticket.priority == Priority.P1, 3),
            (Ticket.priority == Priority.P4, 4),
            else_=5,
        )
        return list(
            self.db.scalars(
                select(TicketAssignment)
                .join(Ticket, Ticket.id == TicketAssignment.ticket_id)
                .where(
                    TicketAssignment.technician_id == technician_id,
                    TicketAssignment.is_active.is_(True),
                )
                .options(selectinload(TicketAssignment.ticket).selectinload(Ticket.attachments))
                .order_by(priority_order, TicketAssignment.assigned_at.asc())
            )
        )

    # ------------------------------------------------------------------ #
    # Mutation helpers (called inside a service transaction)               #
    # ------------------------------------------------------------------ #

    def create_assignment(
        self,
        ticket_id: UUID,
        technician_id: UUID,
        assigned_by_auth_user_id: UUID,
        assignment_note: str | None,
    ) -> TicketAssignment:
        assignment = TicketAssignment(
            ticket_id=ticket_id,
            technician_id=technician_id,
            assigned_by_auth_user_id=assigned_by_auth_user_id,
            status=AssignmentStatus.ASSIGNED,
            assignment_note=assignment_note,
            is_active=True,
        )
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def skill_matches_category(self, technician_id: UUID, category: Category) -> bool:
        return (
            self.db.scalar(
                select(TechnicianSkill).where(
                    TechnicianSkill.technician_id == technician_id,
                    TechnicianSkill.category == category,
                )
            )
            is not None
        )
