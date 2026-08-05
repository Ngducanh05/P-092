"""Resident ticket routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_resident, require_role
from src.database.models.attachment import TicketAttachment
from src.database.models.ticket import Ticket
from src.database.models.user import User
from src.models.api.tickets import TicketAttachmentResponse, TicketCreateRequest, TicketListResponse, TicketResponse
from src.models.enums import Category, Role, TicketStatus
from src.services.ticket_service import TicketService

router = APIRouter()


def bounded_page_size(page_size: int = Query(default=20, ge=1, le=100)) -> int:
    return page_size


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    request: TicketCreateRequest,
    user: User = Depends(require_resident),
    db: Session = Depends(get_db),
) -> TicketResponse:
    ticket = TicketService(db).create_ticket(user, request)
    return ticket_response(ticket)


@router.get("/my", response_model=TicketListResponse)
def my_tickets(
    user: User = Depends(require_resident),
    db: Session = Depends(get_db),
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    category: Category | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Depends(bounded_page_size),
) -> TicketListResponse:
    items, total = TicketService(db).list_my_tickets(
        user, page, page_size, status_filter, category, created_from, created_to
    )
    return TicketListResponse(items=[ticket_response(item) for item in items], page=page, page_size=page_size, total=total)


@router.get("/{ticket_id}", response_model=TicketResponse)
def ticket_detail(
    ticket_id: UUID,
    user: User = Depends(require_role(Role.RESIDENT, Role.COORDINATOR)),
    db: Session = Depends(get_db),
) -> TicketResponse:
    ticket = TicketService(db).get_ticket_for_user(user, ticket_id)
    return ticket_response(ticket)


def ticket_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        category=ticket.category,
        severity=ticket.severity,
        priority=ticket.priority,
        location_description=ticket.location_description,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        attachments=[attachment_response(attachment) for attachment in ticket.attachments],
    )


def attachment_response(attachment: TicketAttachment) -> TicketAttachmentResponse:
    return TicketAttachmentResponse(
        id=attachment.id,
        storage_path=attachment.file_url,
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
    )
