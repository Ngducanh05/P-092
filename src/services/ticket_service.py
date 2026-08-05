"""Ticket business operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from src.database.models.ticket import Ticket
from src.database.models.user import User
from src.models.api.errors import (
    INVALID_ATTACHMENT,
    NO_ACTIVE_UNIT,
    TICKET_NOT_FOUND,
    UNIT_NOT_FOUND,
    UNIT_SELECTION_REQUIRED,
    DomainError,
)
from src.models.api.tickets import TicketCreateRequest
from src.models.enums import Category, Priority, Role, TicketStatus
from src.repositories.ticket_repository import TicketRepository
from src.repositories.unit_repository import UnitRepository
from src.services.storage_service import StorageService


class TicketService:
    def __init__(self, db: Session, storage_service: StorageService | None = None) -> None:
        self.db = db
        self.units = UnitRepository(db)
        self.tickets = TicketRepository(db)
        self.storage = storage_service or StorageService()

    def create_ticket(self, resident: User, request: TicketCreateRequest) -> Ticket:
        active_units = self.units.list_active_memberships_for_user(resident.id)
        if not active_units:
            raise DomainError(NO_ACTIVE_UNIT, "Resident has no active unit.", 400)
        if request.unit_id is None:
            if len(active_units) > 1:
                raise DomainError(UNIT_SELECTION_REQUIRED, "unit_id is required when multiple units are active.", 400)
            unit = active_units[0]
        else:
            unit = self.units.get_authorized_unit_for_user(resident.id, request.unit_id)
            if unit is None:
                raise DomainError(UNIT_NOT_FOUND, "Unit not found.", 404)

        for path in request.attachment_storage_paths:
            if not self.storage.is_owned_ticket_attachment_path(path, resident.id):
                raise DomainError(INVALID_ATTACHMENT, "Invalid attachment path.", 400)
            self.storage.verify_uploaded_object(path)

        try:
            ticket = self.tickets.create_ticket(
                resident_id=resident.id,
                unit_id=unit.id,
                title=request.title,
                description=request.description,
                location=request.location_description,
            )
            self.tickets.create_initial_status_history(ticket.id, resident.id)
            self.tickets.create_attachments(ticket.id, request.attachment_storage_paths)
            self.db.commit()
            self.db.refresh(ticket)
            return ticket
        except Exception:
            self.db.rollback()
            raise

    def list_my_tickets(
        self,
        resident: User,
        page: int,
        page_size: int,
        status: TicketStatus | None = None,
        category: Category | None = None,
        created_from=None,
        created_to=None,
    ):
        return self.tickets.list_resident_accessible_tickets(
            resident.id, page, page_size, status, category, created_from, created_to
        )

    def get_ticket_for_user(self, user: User, ticket_id: UUID) -> Ticket:
        if user.role == Role.COORDINATOR:
            ticket = self.tickets.get_ticket_by_id_for_coordinator(ticket_id)
        else:
            ticket = self.tickets.get_resident_accessible_ticket(user.id, ticket_id)
        if ticket is None:
            raise DomainError(TICKET_NOT_FOUND, "Ticket not found.", 404)
        return ticket

    def list_coordinator_tickets(
        self,
        page: int,
        page_size: int,
        status: TicketStatus | None = None,
        category: Category | None = None,
        priority: Priority | None = None,
        created_from=None,
        created_to=None,
    ):
        return self.tickets.list_coordinator_tickets(page, page_size, status, category, priority, created_from, created_to)
