"""Ticket persistence operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from src.database.models.attachment import TicketAttachment
from src.database.models.ticket import Ticket
from src.database.models.ticket_status_history import TicketStatusHistory
from src.database.models.user_unit_membership import UserUnitMembership
from src.models.enums import Category, Priority, TicketStatus


class TicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_ticket(self, resident_id: UUID, unit_id: UUID, title: str, description: str, location: str | None) -> Ticket:
        ticket = Ticket(
            resident_id=resident_id,
            unit_id=unit_id,
            title=title,
            description=description,
            location_description=location,
            status=TicketStatus.NEW,
        )
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def create_initial_status_history(self, ticket_id: UUID, changed_by_user_id: UUID) -> TicketStatusHistory:
        history = TicketStatusHistory(
            ticket_id=ticket_id,
            from_status=None,
            to_status=TicketStatus.NEW,
            changed_by_user_id=changed_by_user_id,
            change_reason="Ticket created by resident.",
        )
        self.db.add(history)
        self.db.flush()
        return history

    def create_attachments(self, ticket_id: UUID, storage_paths: list[str]) -> list[TicketAttachment]:
        attachments = [
            TicketAttachment(ticket_id=ticket_id, file_url=path, file_type="private_storage", mime_type=None, file_size=None)
            for path in storage_paths
        ]
        self.db.add_all(attachments)
        self.db.flush()
        return attachments

    def list_resident_accessible_tickets(
        self,
        user_id: UUID,
        page: int,
        page_size: int,
        status: TicketStatus | None = None,
        category: Category | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[Ticket], int]:
        query = self._resident_query(user_id)
        query = self._apply_filters(query, status, category, None, created_from, created_to)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = list(
            self.db.scalars(
                query.options(selectinload(Ticket.attachments))
                .order_by(Ticket.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, int(total)

    def get_resident_accessible_ticket(self, user_id: UUID, ticket_id: UUID) -> Ticket | None:
        return self.db.scalar(
            self._resident_query(user_id)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.attachments))
        )

    def list_coordinator_tickets(
        self,
        page: int,
        page_size: int,
        status: TicketStatus | None = None,
        category: Category | None = None,
        priority: Priority | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[Ticket], int]:
        query = self._apply_filters(select(Ticket), status, category, priority, created_from, created_to)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        priority_order = case(
            (Ticket.priority == Priority.P1, 1),
            (Ticket.priority == Priority.P2, 2),
            (Ticket.priority == Priority.P3, 3),
            (Ticket.priority == Priority.P4, 4),
            else_=5,
        )
        items = list(
            self.db.scalars(
                query.options(selectinload(Ticket.attachments))
                .order_by(priority_order, Ticket.created_at.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, int(total)

    def get_ticket_by_id_for_coordinator(self, ticket_id: UUID) -> Ticket | None:
        return self.db.scalar(select(Ticket).where(Ticket.id == ticket_id).options(selectinload(Ticket.attachments)))

    def _resident_query(self, user_id: UUID):
        return (
            select(Ticket)
            .join(UserUnitMembership, UserUnitMembership.unit_id == Ticket.unit_id)
            .where(UserUnitMembership.user_id == user_id, UserUnitMembership.is_active.is_(True))
        )

    def _apply_filters(self, query, status, category, priority, created_from, created_to):
        if status is not None:
            query = query.where(Ticket.status == status)
        if category is not None:
            query = query.where(Ticket.category == category)
        if priority is not None:
            query = query.where(Ticket.priority == priority)
        if created_from is not None:
            query = query.where(Ticket.created_at >= created_from)
        if created_to is not None:
            query = query.where(Ticket.created_at <= created_to)
        return query
