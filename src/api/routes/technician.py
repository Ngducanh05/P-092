"""Technician-only routes for assignment management."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_technician
from src.api.openapi_responses import (
    ATTACHMENT_NOT_FOUND_RESPONSE,
    AUTHENTICATED_RESPONSES,
    INTERNAL_SERVER_ERROR_RESPONSE,
    STORAGE_UNAVAILABLE_RESPONSE,
)
from src.api.routes.storage import get_storage_service
from src.database.models.technician_profile import TechnicianProfile
from src.database.models.ticket_assignment import TicketAssignment
from src.models.api.technicians import (
    AssignmentAttachmentResponse,
    AssignmentResponse,
    AssignmentStatusUpdateRequest,
    AssignmentTicketSummary,
)
from src.models.api.tickets import AttachmentDownloadUrlResponse
from src.services.assignment_service import AssignmentService
from src.services.storage_service import StorageService

router = APIRouter()


def _assignment_response(assignment: TicketAssignment) -> AssignmentResponse:
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
                        f"/api/v1/technician/assignments/{assignment.id}/attachments/"
                        f"{attachment.id}/download-url"
                    ),
                )
                for attachment in ticket.attachments
            ],
        ),
    )


@router.get(
    "/assignments",
    response_model=list[AssignmentResponse],
    summary="List my active assignments",
    description=(
        "Returns all active assignments for the authenticated technician, sorted by ticket "
        "priority then assignment time. Inactive (ended) assignments are not returned."
    ),
    operation_id="list_technician_assignments",
    responses=AUTHENTICATED_RESPONSES,
)
def list_assignments(
    technician: TechnicianProfile = Depends(require_technician),
    db: Session = Depends(get_db),
) -> list[AssignmentResponse]:
    assignments = AssignmentService(db).list_own_assignments(technician.id)
    return [_assignment_response(a) for a in assignments]


@router.get(
    "/assignments/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Get my assignment detail",
    description=(
        "Returns a single active assignment by ID. Returns 404 for another technician's "
        "assignment, an inactive assignment, or a non-existent ID."
    ),
    operation_id="get_technician_assignment",
    responses=AUTHENTICATED_RESPONSES,
)
def get_assignment(
    assignment_id: UUID,
    technician: TechnicianProfile = Depends(require_technician),
    db: Session = Depends(get_db),
) -> AssignmentResponse:
    assignment = AssignmentService(db).get_own_assignment(assignment_id, technician.id)
    return _assignment_response(assignment)


@router.get(
    "/assignments/{assignment_id}/attachments/{attachment_id}/download-url",
    response_model=AttachmentDownloadUrlResponse,
    summary="Create assigned attachment download URL",
    description=(
        "Returns a short-lived signed URL only when the authenticated Technician owns the active assignment "
        "and the attachment belongs to its parent ticket. Foreign assignments and attachments are masked as 404."
    ),
    operation_id="get_technician_assignment_attachment_download_url",
    responses={
        404: ATTACHMENT_NOT_FOUND_RESPONSE,
        **AUTHENTICATED_RESPONSES,
        503: STORAGE_UNAVAILABLE_RESPONSE,
        500: INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
def assignment_attachment_download_url(
    assignment_id: UUID,
    attachment_id: UUID,
    technician: TechnicianProfile = Depends(require_technician),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> AttachmentDownloadUrlResponse:
    attachment, signed_url, expires_in = AssignmentService(db, storage_service).get_own_attachment_download_url(
        assignment_id,
        attachment_id,
        technician.id,
    )
    return AttachmentDownloadUrlResponse(
        attachment_id=attachment.id,
        signed_download_url=signed_url,
        expires_in=expires_in,
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
    )


@router.post(
    "/assignments/{assignment_id}/accept",
    response_model=AssignmentResponse,
    summary="Accept an assignment",
    description=(
        "Transitions the assignment from 'assigned' to 'accepted'. "
        "The parent ticket status is unchanged at this step. "
        "Returns 422 if the assignment is already in a different state."
    ),
    operation_id="accept_technician_assignment",
    responses=AUTHENTICATED_RESPONSES,
)
def accept_assignment(
    assignment_id: UUID,
    technician: TechnicianProfile = Depends(require_technician),
    db: Session = Depends(get_db),
) -> AssignmentResponse:
    assignment = AssignmentService(db).accept_assignment(assignment_id, technician.id)
    return _assignment_response(assignment)


@router.post(
    "/assignments/{assignment_id}/status",
    response_model=AssignmentResponse,
    summary="Update assignment status",
    description=(
        "Transitions the assignment status. Allowed transitions: "
        "accepted → in_progress (sets ticket to in_progress); "
        "assigned/accepted/in_progress → unable_to_handle (requires unable_reason, "
        "returns ticket to waiting_assignment). "
        "Requesting 'completed' is rejected until secure completion evidence is available."
    ),
    operation_id="update_technician_assignment_status",
    responses=AUTHENTICATED_RESPONSES,
)
def update_assignment_status(
    assignment_id: UUID,
    body: AssignmentStatusUpdateRequest,
    technician: TechnicianProfile = Depends(require_technician),
    db: Session = Depends(get_db),
) -> AssignmentResponse:
    assignment = AssignmentService(db).update_assignment_status(
        assignment_id=assignment_id,
        technician_id=technician.id,
        requested_status=body.status,
        unable_reason=body.unable_reason,
        work_note=body.work_note,
    )
    return _assignment_response(assignment)
