"""Resident ticket APIs aligned with Self_Dev_Docs v2."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from src.api.dependencies.auth import CurrentActor, require_resident
from src.api.dependencies.database import get_db
from src.api.routes.storage import get_storage_service
from src.database.models.attachment import TicketAttachment
from src.database.models.ticket import Ticket
from src.models.api.common import ApiResponse
from src.models.api.tickets import (
    AttachmentDownloadUrlResponse,
    ResidentTicketResponse,
    ResidentTimelineItem,
    TicketAttachmentResponse,
    TicketCreatedResponse,
    TicketCreateRequest,
    TicketListResponse,
    TicketSupplementRequest,
)
from src.models.enums import Category, TicketStatus
from src.services.scoring_service import (
    estimated_resolution_text,
    priority_description,
    resident_status_text,
)
from src.services.storage_service import StorageService
from src.services.ticket_service import TicketService

router = APIRouter()


def bounded_page_size(page_size: int = Query(default=20, ge=1, le=100)) -> int:
    return page_size


def _ok(request: Request, data, meta: dict[str, object] | None = None):
    return {"data": data, "meta": meta or {}, "error": None, "request_id": request.state.request_id}


def _resident_actions(ticket: Ticket) -> list[str]:
    actions: list[str] = []
    if ticket.status == TicketStatus.NEW:
        actions.append("CANCEL")
    if ticket.status == TicketStatus.WAITING_RESIDENT_INFO:
        actions.append("SUPPLEMENT_INFORMATION")
    return actions


def _attachment_response(ticket_id: UUID, attachment: TicketAttachment) -> TicketAttachmentResponse:
    return TicketAttachmentResponse(
        id=attachment.id,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        download_url_endpoint=f"/api/v1/tickets/{ticket_id}/attachments/{attachment.id}/download-url",
    )


def resident_ticket_response(ticket: Ticket) -> ResidentTicketResponse:
    return ResidentTicketResponse(
        id=ticket.id,
        description=ticket.description,
        display_status=(
            "Đang phân tích..."
            if ticket.classification_status.value in {"PENDING", "PROCESSING"}
            else resident_status_text(ticket.status)
        ),
        category_display_name=ticket.category.display_name if ticket.category else None,
        priority_description=priority_description(ticket.priority),
        estimated_resolution_text=estimated_resolution_text(ticket.priority, ticket.classification_status),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        available_actions=_resident_actions(ticket),
        attachments=[_attachment_response(ticket.id, a) for a in ticket.attachments],
        timeline=[
            ResidentTimelineItem(
                display_status=resident_status_text(row.to_status),
                reason=row.reason,
                created_at=row.created_at,
            )
            for row in sorted(ticket.status_history, key=lambda item: item.created_at)
        ],
    )


TicketCreateBody = Annotated[TicketCreateRequest, Body()]


@router.post(
    "",
    response_model=ApiResponse[TicketCreatedResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Tạo phản ánh mới",
    description=(
        "Cư dân gửi vị trí và ít nhất text hoặc ảnh. source_unit_id được suy ra từ hồ sơ đã bind; "
        "frontend không được tự gửi ownership ID. Ảnh dùng signed-upload session một lần."
    ),
    operation_id="create_resident_ticket",
)
def create_ticket(
    http_request: Request,
    body: TicketCreateBody,
    actor: CurrentActor = Depends(require_resident),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    ticket = TicketService(db, storage_service).create_ticket(
        actor.user.user_id, actor.resident_profile, body
    )
    return _ok(
        http_request,
        TicketCreatedResponse(
            ticket_id=ticket.id,
            status=ticket.status,
            classification_status=ticket.classification_status,
            display_status="Đang phân tích...",
        ),
    )


@router.get(
    "",
    response_model=ApiResponse[TicketListResponse],
    summary="Danh sách phản ánh của căn hộ hiện tại",
    operation_id="list_resident_tickets",
)
def list_tickets(
    http_request: Request,
    actor: CurrentActor = Depends(require_resident),
    db: Session = Depends(get_db),
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    category: Category | None = Query(default=None),
    created_from: datetime | None = Query(default=None, alias="from"),
    created_to: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Depends(bounded_page_size),
):
    items, total = TicketService(db).list_my_tickets(
        actor.resident_profile,
        page,
        page_size,
        status_filter,
        category,
        created_from,
        created_to,
    )
    data = TicketListResponse(
        items=[resident_ticket_response(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
    return _ok(http_request, data, {"page": page, "page_size": page_size, "total": total})


@router.get(
    "/{ticket_id}",
    response_model=ApiResponse[ResidentTicketResponse],
    summary="Chi tiết phản ánh của căn hộ",
    operation_id="get_resident_ticket",
)
def ticket_detail(
    http_request: Request,
    ticket_id: UUID = Path(),
    actor: CurrentActor = Depends(require_resident),
    db: Session = Depends(get_db),
):
    ticket = TicketService(db).get_ticket(actor.resident_profile, ticket_id)
    return _ok(http_request, resident_ticket_response(ticket))


@router.post(
    "/{ticket_id}/cancel",
    response_model=ApiResponse[ResidentTicketResponse],
    summary="Hủy ticket khi còn NEW",
    operation_id="cancel_resident_ticket",
)
def cancel_ticket(
    http_request: Request,
    ticket_id: UUID,
    actor: CurrentActor = Depends(require_resident),
    db: Session = Depends(get_db),
):
    ticket = TicketService(db).cancel_ticket(actor.user.user_id, actor.resident_profile, ticket_id)
    return _ok(http_request, resident_ticket_response(ticket))


@router.post(
    "/{ticket_id}/supplements",
    response_model=ApiResponse[ResidentTicketResponse],
    summary="Bổ sung thông tin theo yêu cầu BQL",
    operation_id="supplement_resident_ticket",
)
def supplement_ticket(
    http_request: Request,
    ticket_id: UUID,
    body: TicketSupplementRequest,
    actor: CurrentActor = Depends(require_resident),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    ticket = TicketService(db, storage_service).supplement(
        actor.user.user_id, actor.resident_profile, ticket_id, body
    )
    return _ok(http_request, resident_ticket_response(ticket))


@router.get(
    "/{ticket_id}/attachments/{attachment_id}/download-url",
    response_model=ApiResponse[AttachmentDownloadUrlResponse],
    summary="Tạo signed URL cho ảnh thuộc ticket của căn hộ",
)
def attachment_download_url(
    http_request: Request,
    ticket_id: UUID,
    attachment_id: UUID,
    actor: CurrentActor = Depends(require_resident),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    attachment, signed_url, expires_in = TicketService(db, storage_service).get_attachment_download_url(
        actor.resident_profile, ticket_id, attachment_id
    )
    data = AttachmentDownloadUrlResponse(
        attachment_id=attachment.id,
        signed_download_url=signed_url,
        expires_in=expires_in,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
    )
    return _ok(http_request, data)
