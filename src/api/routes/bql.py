"""BQL routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_bql
from src.api.openapi_responses import AUTHENTICATED_RESPONSES
from src.api.routes.tickets import bounded_page_size, ticket_response
from src.database.models.bql_staff import BQLStaff
from src.database.models.technician_profile import TechnicianProfile
from src.models.api.technicians import (
    AssignmentAttachmentResponse,
    AssignmentResponse,
    AssignmentTicketSummary,
    AssignTicketRequest,
    TechnicianListResponse,
    TechnicianSummaryResponse,
)
from src.models.api.tickets import TicketListResponse
from src.models.enums import Category, Priority, TicketStatus
from src.services.assignment_service import AssignmentService
from src.services.ticket_service import TicketService

router = APIRouter()


def _technician_summary(technician: TechnicianProfile) -> TechnicianSummaryResponse:
    return TechnicianSummaryResponse(
        id=technician.id,
        email=technician.email,
        full_name=technician.full_name,
        phone_number=technician.phone_number,
        is_active=technician.is_active,
        is_available=technician.is_available,
        skills=[skill.category.value for skill in technician.skills],
    )


@router.get(
    "/tickets",
    response_model=TicketListResponse,
    summary="List BQL tickets",
    description=(
        "BQL-only endpoint. Returns the system-wide MVP ticket queue with optional status, category, priority, "
        "and ISO 8601 created_at range filters. Results are ordered by priority and creation time, then paginated."
    ),
    operation_id="list_bql_tickets",
    responses=AUTHENTICATED_RESPONSES,
)
def bql_tickets(
    _staff: BQLStaff = Depends(require_bql),
    db: Session = Depends(get_db),
    category: Category | None = Query(default=None, description="Filter by AI-assigned ticket category."),
    priority: Priority | None = Query(default=None, description="Filter by scored ticket priority."),
    status_filter: TicketStatus | None = Query(default=None, alias="status", description="Filter by ticket status."),
    created_from: datetime | None = Query(
        default=None,
        description="Filter tickets created at or after this ISO 8601 timestamp.",
    ),
    created_to: datetime | None = Query(
        default=None,
        description="Filter tickets created at or before this ISO 8601 timestamp.",
    ),
    page: int = Query(default=1, ge=1, description="Page number. Page numbering starts at 1."),
    page_size: int = Depends(bounded_page_size),
) -> TicketListResponse:
    items, total = TicketService(db).list_bql_tickets(
        page, page_size, status_filter, category, priority, created_from, created_to
    )
    return TicketListResponse(items=[ticket_response(item) for item in items], page=page, page_size=page_size, total=total)


@router.get(
    "/technicians",
    response_model=TechnicianListResponse,
    summary="List active technicians",
    description=(
        "BQL-only endpoint. Returns all active technicians with their skill categories for assignment planning."
    ),
    operation_id="list_bql_technicians",
    responses=AUTHENTICATED_RESPONSES,
)
def list_technicians(
    _staff: BQLStaff = Depends(require_bql),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Depends(bounded_page_size),
) -> TechnicianListResponse:
    technicians, total = AssignmentService(db).list_technicians(page, page_size)
    return TechnicianListResponse(
        items=[_technician_summary(t) for t in technicians],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/tickets/{ticket_id}/assign",
    response_model=AssignmentResponse,
    summary="Assign ticket to technician",
    description=(
        "BQL-only endpoint. Assigns an unassigned ticket to an active and available technician. "
        "The technician must have a skill matching the ticket's category. "
        "Commits atomically: creates assignment, updates ticket status, logs notification and audit entry."
    ),
    status_code=201,
    operation_id="bql_assign_ticket",
    responses=AUTHENTICATED_RESPONSES,
)
def assign_ticket(
    ticket_id: UUID,
    body: AssignTicketRequest,
    bql_staff: BQLStaff = Depends(require_bql),
    db: Session = Depends(get_db),
) -> AssignmentResponse:
    assignment = AssignmentService(db).assign_ticket(
        ticket_id=ticket_id,
        technician_id=body.technician_id,
        assigned_by_auth_user_id=bql_staff.id,
        assignment_note=body.assignment_note,
    )
    ticket = assignment.ticket
    return AssignmentResponse(
        id=assignment.id,
        ticket_id=assignment.ticket_id,
        technician_id=assignment.technician_id,
        status=assignment.status,
        assignment_note=assignment.assignment_note,
        work_note=assignment.work_note,
        unable_reason=assignment.unable_reason,
        assigned_at=assignment.assigned_at,
        accepted_at=assignment.accepted_at,
        started_at=assignment.started_at,
        ended_at=assignment.ended_at,
        is_active=assignment.is_active,
        ticket=AssignmentTicketSummary(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            category=ticket.category,
            priority=ticket.priority,
            location_description=ticket.location_description,
            attachments=[
                AssignmentAttachmentResponse(
                    id=attachment.id,
                    mime_type=attachment.mime_type,
                    file_size=attachment.file_size,
                    download_url_endpoint=(
                        f"/api/v1/tickets/{ticket.id}/attachments/{attachment.id}/download-url"
                    ),
                )
                for attachment in ticket.attachments
            ],
        ),
    )
