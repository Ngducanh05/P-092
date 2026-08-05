"""Ticket business operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from src.database.models.attachment import TicketAttachment
from src.database.models.ticket import Ticket
from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession
from src.database.models.user import User
from src.models.api.errors import (
    ATTACHMENT_NOT_FOUND,
    INVALID_ATTACHMENT,
    NO_ACTIVE_UNIT,
    STORAGE_NOT_CONFIGURED,
    TICKET_NOT_FOUND,
    UNIT_NOT_FOUND,
    UNIT_SELECTION_REQUIRED,
    DomainError,
)
from src.models.api.tickets import TicketCreateRequest
from src.models.enums import Category, Priority, Role, TicketStatus
from src.repositories.ticket_repository import TicketRepository
from src.repositories.unit_repository import UnitRepository
from src.services.storage_service import StorageService


class TicketService:
    def __init__(self, db: Session, storage_service: StorageService | None = None) -> None:
        self.db = db
        self.units = UnitRepository(db)
        self.tickets = TicketRepository(db)
        self.storage = storage_service or StorageService()

    def create_ticket(self, resident: User, request: TicketCreateRequest) -> Ticket:
        active_units = self.units.list_active_memberships_for_user(resident.id)
        if not active_units:
            raise DomainError(NO_ACTIVE_UNIT, "Resident has no active unit.", 400)
        if request.unit_id is None:
            if len(active_units) > 1:
                raise DomainError(UNIT_SELECTION_REQUIRED, "unit_id is required when multiple units are active.", 400)
            unit = active_units[0]
        else:
            unit = self.units.get_authorized_unit_for_user(resident.id, request.unit_id)
            if unit is None:
                raise DomainError(UNIT_NOT_FOUND, "Unit not found.", 404)

        try:
            upload_sessions = self._lock_and_verify_upload_sessions(resident.id, request.attachment_upload_ids)
            ticket = self.tickets.create_ticket(
                resident_id=resident.id,
                unit_id=unit.id,
                title=request.title,
                description=request.description,
                location=request.location_description,
            )
            self.tickets.create_initial_status_history(ticket.id, resident.id)
            self.tickets.create_attachments_from_upload_sessions(ticket.id, upload_sessions)
            self.tickets.mark_upload_sessions_consumed(upload_sessions)
            self.db.commit()
            self.db.refresh(ticket)
            return ticket
        except Exception:
            self.db.rollback()
            raise

    def list_my_tickets(
        self,
        resident: User,
        page: int,
        page_size: int,
        status: TicketStatus | None = None,
        category: Category | None = None,
        created_from=None,
        created_to=None,
    ):
        return self.tickets.list_resident_accessible_tickets(
            resident.id, page, page_size, status, category, created_from, created_to
        )

    def get_ticket_for_user(self, user: User, ticket_id: UUID) -> Ticket:
        if user.role == Role.COORDINATOR:
            ticket = self.tickets.get_ticket_by_id_for_coordinator(ticket_id)
        else:
            ticket = self.tickets.get_resident_accessible_ticket(user.id, ticket_id)
        if ticket is None:
            raise DomainError(TICKET_NOT_FOUND, "Ticket not found.", 404)
        return ticket

    def get_attachment_download_url_for_user(
        self,
        user: User,
        ticket_id: UUID,
        attachment_id: UUID,
    ) -> tuple[TicketAttachment, str, int]:
        try:
            ticket = self.get_ticket_for_user(user, ticket_id)
        except DomainError as exc:
            if exc.code == TICKET_NOT_FOUND:
                raise DomainError(ATTACHMENT_NOT_FOUND, "Attachment not found.", 404) from exc
            raise
        attachment = self.tickets.get_attachment_for_ticket(ticket.id, attachment_id)
        if attachment is None:
            raise DomainError(ATTACHMENT_NOT_FOUND, "Attachment not found.", 404)
        signed_url = self.storage.create_signed_download_url(attachment.file_url)
        return attachment, signed_url, self.storage.settings.supabase_signed_download_ttl_seconds

    def list_coordinator_tickets(
        self,
        page: int,
        page_size: int,
        status: TicketStatus | None = None,
        category: Category | None = None,
        priority: Priority | None = None,
        created_from=None,
        created_to=None,
    ):
        return self.tickets.list_coordinator_tickets(page, page_size, status, category, priority, created_from, created_to)

    def _lock_and_verify_upload_sessions(
        self,
        resident_id: UUID,
        upload_ids: list[UUID],
    ) -> list[TicketAttachmentUploadSession]:
        if not upload_ids:
            return []
        upload_sessions = self.tickets.lock_upload_sessions(upload_ids)
        by_id = {upload_session.id: upload_session for upload_session in upload_sessions}
        if set(by_id) != set(upload_ids):
            raise DomainError(INVALID_ATTACHMENT, "Invalid attachment upload session.", 400)
        ordered_sessions = [by_id[upload_id] for upload_id in upload_ids]
        now = datetime.now(UTC)
        verified_at = now
        for upload_session in ordered_sessions:
            if upload_session.owner_user_id != resident_id:
                raise DomainError(INVALID_ATTACHMENT, "Invalid attachment upload session.", 400)
            if upload_session.status != "pending" or upload_session.consumed_at is not None:
                raise DomainError(INVALID_ATTACHMENT, "Invalid attachment upload session.", 400)
            expires_at = upload_session.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= now:
                raise DomainError(INVALID_ATTACHMENT, "Attachment upload session has expired.", 400)
            if not self.storage.is_owned_ticket_attachment_path(upload_session.storage_path, resident_id):
                raise DomainError(INVALID_ATTACHMENT, "Invalid attachment upload session.", 400)
            try:
                verified = self.storage.verify_uploaded_object(
                    upload_session.storage_path,
                    expected_mime_type=upload_session.mime_type,
                    expected_file_size=upload_session.file_size,
                )
            except DomainError as exc:
                if exc.code == STORAGE_NOT_CONFIGURED:
                    raise
                raise
            verified_at = verified.verified_at
        self.tickets.mark_upload_sessions_verified(ordered_sessions, verified_at)
        return ordered_sessions
