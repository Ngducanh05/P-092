"""Supabase Storage signed URL operations."""

from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import UUID, uuid4

import httpx

from src.config import Settings, get_settings
from src.models.api.errors import INVALID_ATTACHMENT, STORAGE_NOT_CONFIGURED, DomainError
from src.models.api.storage import SignedUploadRequest, SignedUploadResponse

SAFE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def create_signed_upload_url(self, user_id: UUID, request: SignedUploadRequest) -> SignedUploadResponse:
        self._validate_metadata(request)
        storage_path = self.generate_ticket_attachment_path(user_id, request.original_filename, request.mime_type)
        if not self._is_configured():
            raise DomainError(STORAGE_NOT_CONFIGURED, "Supabase Storage is not configured.", 503)
        response = httpx.post(
            f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/upload/sign/"
            f"{self.settings.supabase_storage_bucket}/{storage_path}",
            headers=self._service_headers(),
            timeout=10.0,
        )
        if response.status_code >= 400:
            raise DomainError(STORAGE_NOT_CONFIGURED, "Unable to create signed upload URL.", 503)
        data = response.json()
        signed_url = data.get("signedURL") or data.get("signed_url")
        token = data.get("token")
        return SignedUploadResponse(
            storage_path=storage_path,
            signed_upload_url=signed_url,
            signed_upload_token=token,
            expires_in=self.settings.supabase_signed_upload_ttl_seconds,
            required_headers={"content-type": request.mime_type},
        )

    def create_signed_download_url(self, storage_path: str) -> str:
        if not self._is_configured():
            raise DomainError(STORAGE_NOT_CONFIGURED, "Supabase Storage is not configured.", 503)
        response = httpx.post(
            f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/sign/"
            f"{self.settings.supabase_storage_bucket}/{storage_path}",
            headers=self._service_headers(),
            json={"expiresIn": self.settings.supabase_signed_download_ttl_seconds},
            timeout=10.0,
        )
        if response.status_code >= 400:
            raise DomainError(STORAGE_NOT_CONFIGURED, "Unable to create signed download URL.", 503)
        return str(response.json().get("signedURL") or response.json().get("signed_url"))

    def generate_ticket_attachment_path(self, user_id: UUID, original_filename: str, mime_type: str) -> str:
        self._reject_path_traversal(original_filename)
        now = datetime.now(UTC)
        extension = SAFE_EXTENSIONS.get(mime_type) or mimetypes.guess_extension(mime_type)
        if extension not in SAFE_EXTENSIONS.values():
            raise DomainError(INVALID_ATTACHMENT, "Unsupported image type.", 400)
        return f"tickets/{user_id}/{now:%Y}/{now:%m}/{uuid4()}{extension}"

    def is_owned_ticket_attachment_path(self, storage_path: str, user_id: UUID) -> bool:
        self._reject_path_traversal(storage_path)
        return storage_path.startswith(f"tickets/{user_id}/")

    def verify_uploaded_object(self, storage_path: str) -> None:
        self._reject_path_traversal(storage_path)
        if not self._is_configured():
            return
        response = httpx.head(
            f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/"
            f"{self.settings.supabase_storage_bucket}/{storage_path}",
            headers=self._service_headers(),
            timeout=10.0,
        )
        if response.status_code == 404:
            raise DomainError(INVALID_ATTACHMENT, "Uploaded attachment object was not found.", 400)
        if response.status_code >= 400:
            raise DomainError(STORAGE_NOT_CONFIGURED, "Unable to verify uploaded object.", 503)

    def _validate_metadata(self, request: SignedUploadRequest) -> None:
        if request.mime_type not in self.settings.parsed_allowed_ticket_image_mime_types:
            raise DomainError(INVALID_ATTACHMENT, "Unsupported image type.", 400)
        if request.mime_type == "image/svg+xml":
            raise DomainError(INVALID_ATTACHMENT, "SVG images are not allowed.", 400)
        if request.file_size > self.settings.max_ticket_image_bytes:
            raise DomainError(INVALID_ATTACHMENT, "Image is too large.", 400)
        self._reject_path_traversal(request.original_filename)

    def _reject_path_traversal(self, value: str) -> None:
        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise DomainError(INVALID_ATTACHMENT, "Invalid attachment path.", 400)

    def _is_configured(self) -> bool:
        return bool(self.settings.supabase_url and self.settings.supabase_secret_key)

    def _service_headers(self) -> dict[str, str]:
        return {
            "apikey": self.settings.supabase_secret_key,
            "Authorization": f"Bearer {self.settings.supabase_secret_key}",
        }
