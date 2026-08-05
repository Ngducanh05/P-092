"""Storage routes."""

from fastapi import APIRouter, Depends

from src.api.dependencies.roles import require_resident
from src.database.models.user import User
from src.models.api.storage import SignedUploadRequest, SignedUploadResponse
from src.services.storage_service import StorageService

router = APIRouter()


@router.post("/ticket-attachments/upload-url", response_model=SignedUploadResponse)
def create_ticket_attachment_upload_url(
    request: SignedUploadRequest,
    user: User = Depends(require_resident),
) -> SignedUploadResponse:
    return StorageService().create_signed_upload_url(user.id, request)
