"""Storage routes."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_resident
from src.api.openapi_responses import (
    AUTHENTICATED_RESPONSES,
    BAD_REQUEST_RESPONSE,
    INTERNAL_SERVER_ERROR_RESPONSE,
    STORAGE_UNAVAILABLE_RESPONSE,
)
from src.database.models.resident import Resident
from src.models.api.storage import SignedUploadRequest, SignedUploadResponse
from src.repositories.ticket_repository import TicketRepository
from src.services.storage_service import StorageService

router = APIRouter()


def get_storage_service() -> StorageService:
    return StorageService()


SignedUploadBody = Annotated[
    SignedUploadRequest,
    Body(
        openapi_examples={
            "water_leak_image": {
                "summary": "Image attachment upload target",
                "value": {
                    "original_filename": "water-leak.jpg",
                    "mime_type": "image/jpeg",
                    "file_size": 245760,
                },
            }
        }
    ),
]


@router.post(
    "/ticket-attachments/upload-url",
    response_model=SignedUploadResponse,
    summary="Create ticket attachment upload URL",
    description=(
        "Resident-only endpoint. Creates a private Supabase Storage signed upload target and records an upload "
        "session owned by the authenticated resident. The response returns an upload session ID plus signed upload "
        "details; it never returns the private Storage object path. The upload session can later be consumed by "
        "ticket creation."
    ),
    operation_id="create_ticket_attachment_upload_url",
    responses={
        400: BAD_REQUEST_RESPONSE,
        **AUTHENTICATED_RESPONSES,
        503: {
            **STORAGE_UNAVAILABLE_RESPONSE,
            "description": "Supabase Auth or Supabase Storage is unavailable or not configured.",
        },
        500: INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
def create_ticket_attachment_upload_url(
    request: SignedUploadBody,
    resident: Resident = Depends(require_resident),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> SignedUploadResponse:
    target = storage_service.create_signed_upload_target(resident.id, request)
    try:
        upload_session = TicketRepository(db).create_upload_session(
            resident_id=resident.id,
            storage_path=target.storage_path,
            original_filename=request.original_filename,
            mime_type=request.mime_type,
            file_size=request.file_size,
        )
        db.commit()
        db.refresh(upload_session)
    except Exception:
        db.rollback()
        raise
    return SignedUploadResponse(
        upload_id=upload_session.id,
        signed_upload_url=target.signed_upload_url,
        signed_upload_token=target.signed_upload_token,
        expires_in=target.expires_in,
        required_headers=target.required_headers,
    )
