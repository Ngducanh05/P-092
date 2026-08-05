"""Storage routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_resident
from src.database.models.user import User
from src.models.api.storage import SignedUploadRequest, SignedUploadResponse
from src.repositories.ticket_repository import TicketRepository
from src.services.storage_service import StorageService

router = APIRouter()


def get_storage_service() -> StorageService:
    return StorageService()


@router.post("/ticket-attachments/upload-url", response_model=SignedUploadResponse)
def create_ticket_attachment_upload_url(
    request: SignedUploadRequest,
    user: User = Depends(require_resident),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> SignedUploadResponse:
    target = storage_service.create_signed_upload_target(user.id, request)
    try:
        upload_session = TicketRepository(db).create_upload_session(
            owner_user_id=user.id,
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
