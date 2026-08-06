"""Resident ticket routes."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies.auth import CurrentActor, get_current_actor
from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_resident
from src.api.openapi_responses import (
    ATTACHMENT_NOT_FOUND_RESPONSE,
    AUTHENTICATED_RESPONSES,
    BAD_REQUEST_RESPONSE,
    INTERNAL_SERVER_ERROR_RESPONSE,
    STORAGE_UNAVAILABLE_RESPONSE,
    TICKET_NOT_FOUND_RESPONSE,
    UNIT_NOT_FOUND_RESPONSE,
)
from src.database.models.attachment import TicketAttachment
from src.database.models.resident import Resident
from src.database.models.ticket import Ticket
from src.models.api.tickets import (
    AttachmentDownloadUrlResponse,
    TicketAttachmentResponse,
    TicketCreateRequest,
    TicketListResponse,
    TicketResponse,
)
from src.models.enums import Category, TicketStatus
from src.services.ticket_service import TicketService

router = APIRouter()


def bounded_page_size(
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page. Must be between 1 and 100.",
    ),
) -> int:
    return page_size


TicketCreateBody = Annotated[
    TicketCreateRequest,
    Body(
        openapi_examples={
            "water_leak": {
                "summary": "Resident water leak ticket",
                "value": {
                    "title": "Rò rỉ nước tại hành lang tầng 10",
                    "description": "Nước đang chảy từ trần gần thang máy và làm sàn bị trơn.",
                    "unit_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "location_description": "Hành lang tầng 10, trước thang máy số 2",
                    "attachment_upload_ids": ["6ba7b810-9dad-11d1-80b4-00c04fd430c8"],
                },
            }
        }
    ),
]


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a resident ticket",
    description=(
        "Resident-only endpoint. Creates a maintenance ticket for an active unit membership. If the resident has "
        "multiple active units, unit_id is required. Valid attachment upload sessions are locked, verified against "
        "private Supabase Storage, converted into attachment metadata, and consumed in the same database transaction "
        "as ticket creation. Raw private Storage paths are never accepted from the client."
    ),
    operation_id="create_ticket",
    responses={
        400: BAD_REQUEST_RESPONSE,
        404: UNIT_NOT_FOUND_RESPONSE,
        **AUTHENTICATED_RESPONSES,
        503: {
            **STORAGE_UNAVAILABLE_RESPONSE,
            "description": "Supabase Auth or Supabase Storage is unavailable or not configured.",
        },
        500: INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
def create_ticket(
    request: TicketCreateBody,
    resident: Resident = Depends(require_resident),
    db: Session = Depends(get_db),
) -> TicketResponse:
    ticket = TicketService(db).create_ticket(resident, request)
    return ticket_response(ticket)


@router.get(
    "/my",
    response_model=TicketListResponse,
    summary="List my tickets",
    description=(
        "Resident-only endpoint. Returns tickets accessible through the authenticated resident's active unit "
        "memberships. Supports optional status, category, and ISO 8601 created_at range filters. Results are ordered "
        "by newest first and paginated; page numbering starts at 1 and page_size must be between 1 and 100."
    ),
    operation_id="list_my_tickets",
    responses=AUTHENTICATED_RESPONSES,
)
def my_tickets(
    resident: Resident = Depends(require_resident),
    db: Session = Depends(get_db),
    status_filter: TicketStatus | None = Query(default=None, alias="status", description="Filter by ticket status."),
    category: Category | None = Query(default=None, description="Filter by AI-assigned ticket category."),
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
    items, total = TicketService(db).list_my_tickets(
        resident, page, page_size, status_filter, category, created_from, created_to
    )
    return TicketListResponse(items=[ticket_response(item) for item in items], page=page, page_size=page_size, total=total)


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get ticket detail",
    description=(
        "Resident or BQL endpoint. Residents can retrieve only tickets accessible through active unit "
        "membership. BQL can retrieve any ticket for the current MVP. For residents, the endpoint returns "
        "404 both when the ticket does not exist and when the resident is not authorized, avoiding resource "
        "existence leaks."
    ),
    operation_id="get_ticket",
    responses={
        404: TICKET_NOT_FOUND_RESPONSE,
        **AUTHENTICATED_RESPONSES,
    },
)
def ticket_detail(
    ticket_id: UUID = Path(description="Ticket UUID to retrieve."),
    actor: CurrentActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    if actor.actor_type == "resident":
        ticket = service.get_ticket_for_resident(actor.profile, ticket_id)
    else:
        ticket = service.get_ticket_for_bql(actor.profile, ticket_id)
    return ticket_response(ticket)


@router.get(
    "/{ticket_id}/attachments/{attachment_id}/download-url",
    response_model=AttachmentDownloadUrlResponse,
    summary="Create attachment download URL",
    description=(
        "Resident or BQL endpoint. Returns a short-lived signed Supabase Storage download URL for an "
        "attachment that belongs to the requested ticket and is visible to the current user. The response contains "
        "a signed URL, not a public URL and not the private Storage object path. Missing tickets, unauthorized "
        "resident access, and missing attachments are all reported as 404 attachment not found."
    ),
    operation_id="get_ticket_attachment_download_url",
    responses={
        404: ATTACHMENT_NOT_FOUND_RESPONSE,
        **AUTHENTICATED_RESPONSES,
        503: {
            **STORAGE_UNAVAILABLE_RESPONSE,
            "description": "Supabase Auth or Supabase Storage is unavailable or not configured.",
        },
        500: INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
def attachment_download_url(
    ticket_id: UUID = Path(description="Ticket UUID that owns the attachment."),
    attachment_id: UUID = Path(description="Attachment UUID to sign for download."),
    actor: CurrentActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> AttachmentDownloadUrlResponse:
    service = TicketService(db)
    if actor.actor_type == "resident":
        attachment, signed_url, expires_in = service.get_attachment_download_url_for_resident(
            actor.profile, ticket_id, attachment_id
        )
    else:
        attachment, signed_url, expires_in = service.get_attachment_download_url_for_bql(
            actor.profile, ticket_id, attachment_id
        )
    return AttachmentDownloadUrlResponse(
        attachment_id=attachment.id,
        signed_download_url=signed_url,
        expires_in=expires_in,
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
    )


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
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
        download_url_endpoint=f"/api/v1/tickets/{attachment.ticket_id}/attachments/{attachment.id}/download-url",
    )
