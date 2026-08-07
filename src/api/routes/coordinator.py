"""Coordinator/BQL APIs defined by Self_Dev_Docs v2.

There is deliberately no Technician assignment workflow. Coordinators move an
approved ticket directly through IN_PROGRESS to COMPLETED/UNRESOLVABLE.
"""

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.api.dependencies.auth import CurrentActor, require_coordinator
from src.api.dependencies.database import get_db
from src.api.routes.storage import get_storage_service
from src.models.api.common import ApiResponse
from src.models.api.coordinator import (
    AuditLogResponse,
    ClassificationOverrideRequest,
    CoordinatorAnalysisSummary,
    CoordinatorTicketListResponse,
    CoordinatorTicketResponse,
    ExportReportRequest,
    ManualReviewResolveRequest,
    RequestInformationRequest,
    SlaPerformanceReport,
    TicketSummaryReport,
)
from src.models.api.tickets import AttachmentDownloadUrlResponse, TicketAttachmentResponse, TicketTimelineItem
from src.models.enums import Category, ClassificationStatus, Priority, TicketStatus
from src.services.coordinator_service import CoordinatorService
from src.services.storage_service import StorageService

router = APIRouter()


def _ok(request: Request, data, meta: dict[str, object] | None = None):
    return {"data": data, "meta": meta or {}, "error": None, "request_id": request.state.request_id}


def _available_actions(ticket) -> list[str]:
    actions: list[str] = []
    if ticket.classification_status == ClassificationStatus.MANUAL_REVIEW:
        actions.append("RESOLVE_MANUAL_REVIEW")
    if ticket.status == TicketStatus.NEW:
        actions.append("REQUEST_INFORMATION")
        if (
            ticket.classification_status == ClassificationStatus.RESOLVED
            and ticket.category_id is not None
            and ticket.priority is not None
        ):
            actions.append("APPROVE")
    if ticket.status == TicketStatus.APPROVED:
        actions.append("START")
    if ticket.status == TicketStatus.IN_PROGRESS:
        actions.extend(["COMPLETE", "UNRESOLVABLE"])
    # Self Dev v2 allows a Coordinator to correct Category/Priority on any ticket.
    actions.append("OVERRIDE_CLASSIFICATION")
    return actions


def _latest_analysis_summary(ticket) -> CoordinatorAnalysisSummary | None:
    if not ticket.ai_analysis_runs:
        return None
    run = max(ticket.ai_analysis_runs, key=lambda item: item.run_number)
    return CoordinatorAnalysisSummary(
        run_number=run.run_number,
        text_categories=[Category(value) for value in run.text_categories],
        image_categories=(
            [Category(value) for value in run.image_categories]
            if run.image_categories is not None
            else None
        ),
        red_flag_text=run.red_flag_text,
        red_flag_signal=run.red_flag_signal,
        severity=run.severity,
        severity_source=run.severity_source,
        text_model_version=run.text_model_version,
        vision_model_version=run.vision_model_version,
        error_code=run.error_code,
    )


def coordinator_ticket_response(ticket) -> CoordinatorTicketResponse:
    return CoordinatorTicketResponse(
        id=ticket.id,
        reporter_user_id=ticket.reporter_user_id,
        source_unit_id=ticket.source_unit_id,
        location_id=ticket.location_id,
        location_label=ticket.location.label if ticket.location else None,
        description=ticket.description,
        status=ticket.status,
        classification_status=ticket.classification_status,
        display_code="P0" if ticket.classification_status == ClassificationStatus.MANUAL_REVIEW else None,
        category_id=ticket.category_id,
        category=ticket.category.code if ticket.category else None,
        priority=ticket.priority,
        severity=ticket.severity,
        red_flag_detected=ticket.red_flag_detected,
        score_total=float(ticket.score_total) if ticket.score_total is not None else None,
        sla_started_at=ticket.sla_started_at,
        sla_due_at=ticket.sla_due_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        version=ticket.version,
        available_actions=_available_actions(ticket),
        latest_analysis=_latest_analysis_summary(ticket),
        attachments=[
            TicketAttachmentResponse(
                id=a.id,
                mime_type=a.mime_type,
                size_bytes=a.size_bytes,
                download_url_endpoint=(
                    f"/api/v1/coordinator/tickets/{ticket.id}/attachments/{a.id}/download-url"
                ),
            )
            for a in ticket.attachments
        ],
        timeline=[
            TicketTimelineItem(
                from_status=row.from_status,
                to_status=row.to_status,
                reason=row.reason,
                created_at=row.created_at,
            )
            for row in sorted(ticket.status_history, key=lambda item: item.created_at)
        ],
    )


@router.get("/tickets", response_model=ApiResponse[CoordinatorTicketListResponse], summary="Dashboard ticket BQL")
def list_tickets(
    http_request: Request,
    _actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
    category: Category | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    classification_status: ClassificationStatus | None = Query(default=None),
    created_from: datetime | None = Query(default=None, alias="from"),
    created_to: datetime | None = Query(default=None, alias="to"),
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    items, total = CoordinatorService(db).list_tickets(
        page,
        page_size,
        status=status_filter,
        category=category,
        priority=priority,
        classification_status=classification_status,
        created_from=created_from,
        created_to=created_to,
        search=search,
    )
    data = CoordinatorTicketListResponse(
        items=[coordinator_ticket_response(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
    return _ok(http_request, data, {"page": page, "page_size": page_size, "total": total})


@router.get("/tickets/{ticket_id}", response_model=ApiResponse[CoordinatorTicketResponse], summary="Chi tiết ticket BQL")
def get_ticket(
    http_request: Request,
    ticket_id: UUID,
    _actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    return _ok(http_request, coordinator_ticket_response(CoordinatorService(db).get_ticket(ticket_id)))


@router.post(
    "/tickets/{ticket_id}/manual-review/resolve",
    response_model=ApiResponse[CoordinatorTicketResponse],
    summary="Xử lý P0/manual review",
)
def resolve_manual_review(
    http_request: Request,
    ticket_id: UUID,
    body: ManualReviewResolveRequest,
    actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    ticket = CoordinatorService(db).resolve_manual_review(actor.user.user_id, ticket_id, body)
    return _ok(http_request, coordinator_ticket_response(ticket))


@router.post(
    "/tickets/{ticket_id}/request-information",
    response_model=ApiResponse[CoordinatorTicketResponse],
    summary="Yêu cầu Cư dân bổ sung thông tin",
)
def request_information(
    http_request: Request,
    ticket_id: UUID,
    body: RequestInformationRequest,
    actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    ticket = CoordinatorService(db).request_information(actor.user.user_id, ticket_id, body.message)
    return _ok(http_request, coordinator_ticket_response(ticket))


@router.post("/tickets/{ticket_id}/approve", response_model=ApiResponse[CoordinatorTicketResponse], summary="Duyệt ticket")
def approve_ticket(
    http_request: Request,
    ticket_id: UUID,
    actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    ticket = CoordinatorService(db).approve(actor.user.user_id, ticket_id)
    return _ok(http_request, coordinator_ticket_response(ticket))


@router.patch(
    "/tickets/{ticket_id}/classification",
    response_model=ApiResponse[CoordinatorTicketResponse],
    summary="Override Category/Priority với audit",
)
def override_classification(
    http_request: Request,
    ticket_id: UUID,
    body: ClassificationOverrideRequest,
    actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    ticket = CoordinatorService(db).override_classification(actor.user.user_id, ticket_id, body)
    return _ok(http_request, coordinator_ticket_response(ticket))


@router.post("/tickets/{ticket_id}/start", response_model=ApiResponse[CoordinatorTicketResponse], summary="Bắt đầu xử lý ticket")
def start_ticket(
    http_request: Request,
    ticket_id: UUID,
    actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    ticket = CoordinatorService(db).start(actor.user.user_id, ticket_id)
    return _ok(http_request, coordinator_ticket_response(ticket))


@router.post("/tickets/{ticket_id}/complete", response_model=ApiResponse[CoordinatorTicketResponse], summary="Hoàn thành ticket")
def complete_ticket(
    http_request: Request,
    ticket_id: UUID,
    actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    ticket = CoordinatorService(db).complete(actor.user.user_id, ticket_id)
    return _ok(http_request, coordinator_ticket_response(ticket))


@router.post(
    "/tickets/{ticket_id}/unresolvable",
    response_model=ApiResponse[CoordinatorTicketResponse],
    summary="Đánh dấu ticket không xử lý được",
)
def mark_unresolvable(
    http_request: Request,
    ticket_id: UUID,
    actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    ticket = CoordinatorService(db).unresolvable(actor.user.user_id, ticket_id)
    return _ok(http_request, coordinator_ticket_response(ticket))


@router.get(
    "/tickets/{ticket_id}/attachments/{attachment_id}/download-url",
    response_model=ApiResponse[AttachmentDownloadUrlResponse],
    summary="Signed URL ảnh cho BQL",
)
def coordinator_attachment_download_url(
    http_request: Request,
    ticket_id: UUID,
    attachment_id: UUID,
    _actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    service = CoordinatorService(db)
    ticket = service.get_ticket(ticket_id)
    attachment = service.tickets.get_attachment(ticket.id, attachment_id)
    if attachment is None:
        from src.models.api.errors import ATTACHMENT_NOT_FOUND, DomainError

        raise DomainError(ATTACHMENT_NOT_FOUND, "Attachment không tồn tại.", 404)
    signed_url = storage_service.create_signed_download_url(attachment.object_path)
    data = AttachmentDownloadUrlResponse(
        attachment_id=attachment.id,
        signed_download_url=signed_url,
        expires_in=storage_service.settings.supabase_signed_download_ttl_seconds,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
    )
    return _ok(http_request, data)


@router.get("/audit-logs", response_model=ApiResponse[list[AuditLogResponse]], summary="Audit log")
def audit_logs(
    http_request: Request,
    _actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
    actor_user_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    created_from: datetime | None = Query(default=None, alias="from"),
    created_to: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=500),
):
    rows = CoordinatorService(db).list_audit_logs(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
    )
    data = [
        AuditLogResponse(
            id=row.id,
            actor_user_id=row.actor_user_id,
            actor_role=row.actor_role,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            before_data=row.before_data,
            after_data=row.after_data,
            reason=row.reason,
            request_id=row.request_id,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return _ok(http_request, data)


@router.get(
    "/reports/tickets-summary",
    response_model=ApiResponse[TicketSummaryReport],
    summary="Báo cáo tổng hợp ticket",
)
def tickets_summary(
    http_request: Request,
    _actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    return _ok(http_request, TicketSummaryReport(**CoordinatorService(db).tickets_summary()))


@router.get(
    "/reports/sla-performance",
    response_model=ApiResponse[SlaPerformanceReport],
    summary="Báo cáo tuân thủ thời gian xử lý",
)
def sla_performance(
    http_request: Request,
    _actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    return _ok(http_request, SlaPerformanceReport(**CoordinatorService(db).sla_performance()))


@router.post("/reports/export", summary="Xuất báo cáo CSV")
def export_report(
    body: ExportReportRequest,
    _actor: CurrentActor = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    service = CoordinatorService(db)
    output = io.StringIO()
    writer = csv.writer(output)
    if body.report == "sla-performance":
        report = service.sla_performance()
        writer.writerow(["metric", "value"])
        for key, value in report.items():
            writer.writerow([key, value])
    else:
        report = service.tickets_summary()
        writer.writerow(["section", "key", "value"])
        writer.writerow(["summary", "total", report["total"]])
        for section in ("by_status", "by_priority", "by_category"):
            for key, value in report[section].items():
                writer.writerow([section, key, value])
    payload = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([payload]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{body.report}.csv"'},
    )
