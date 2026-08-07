"""Resident ticket business operations aligned with Self_Dev_Docs v2."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from src.database.models.attachment import TicketAttachment
from src.database.models.resident_profile import ResidentProfile
from src.database.models.ticket import Ticket
from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession
from src.models.api.errors import (
    ATTACHMENT_NOT_FOUND,
    INFORMATION_REQUEST_NOT_FOUND,
    INVALID_ATTACHMENT,
    INVALID_LOCATION,
    INVALID_STATUS_TRANSITION,
    NO_ACTIVE_UNIT,
    STORAGE_NOT_CONFIGURED,
    TICKET_NOT_FOUND,
    DomainError,
)
from src.models.api.tickets import TicketCreateRequest, TicketSupplementRequest
from src.models.enums import AttachmentType, Category, ClassificationStatus, InformationRequestStatus, TicketStatus
from src.repositories.catalog_repository import CatalogRepository
from src.repositories.ticket_repository import TicketRepository
from src.services.storage_service import StorageService


class TicketService:
    def __init__(self, db: Session, storage_service: StorageService | None = None) -> None:
        self.db = db
        self.catalog = CatalogRepository(db)
        self.tickets = TicketRepository(db)
        self.storage = storage_service or StorageService()

    def create_ticket(self, user_id: UUID, resident_profile: ResidentProfile | None, request: TicketCreateRequest) -> Ticket:
        if resident_profile is None:
            raise DomainError(NO_ACTIVE_UNIT, "Tài khoản chưa liên kết căn hộ.", 400)
        location = self.catalog.get_location(request.location_id)
        if location is None:
            raise DomainError(INVALID_LOCATION, "Vị trí không hợp lệ.", 400)
        if location.building_id != resident_profile.unit.building_id:
            raise DomainError(INVALID_LOCATION, "Vị trí không thuộc tòa nhà của căn hộ hiện tại.", 400)
        if location.unit_id is not None and location.unit_id != resident_profile.unit_id:
            raise DomainError(INVALID_LOCATION, "Vị trí trong căn hộ không thuộc tài khoản hiện tại.", 400)

        try:
            sessions = self._lock_and_verify_upload_sessions(user_id, request.attachment_upload_ids)
            ticket = self.tickets.create_ticket(
                reporter_user_id=user_id,
                source_unit_id=resident_profile.unit_id,
                location_id=location.id,
                description=request.description,
            )
            self.tickets.append_status_history(
                ticket,
                from_status=None,
                to_status=TicketStatus.NEW,
                changed_by=user_id,
                reason="Resident created ticket.",
            )
            self.tickets.create_attachments_from_upload_sessions(ticket.id, user_id, sessions)
            self.tickets.mark_upload_sessions_consumed(sessions)
            self.db.commit()
            return self.tickets.get_resident_ticket(resident_profile.unit_id, ticket.id) or ticket
        except Exception:
            self.db.rollback()
            raise

    def list_my_tickets(
        self,
        resident_profile: ResidentProfile | None,
        page: int,
        page_size: int,
        status: TicketStatus | None = None,
        category: Category | None = None,
        created_from=None,
        created_to=None,
    ):
        if resident_profile is None:
            raise DomainError(NO_ACTIVE_UNIT, "Tài khoản chưa liên kết căn hộ.", 400)
        return self.tickets.list_resident_tickets(
            resident_profile.unit_id,
            page,
            page_size,
            status=status,
            category=category,
            created_from=created_from,
            created_to=created_to,
        )

    def get_ticket(self, resident_profile: ResidentProfile | None, ticket_id: UUID) -> Ticket:
        if resident_profile is None:
            raise DomainError(NO_ACTIVE_UNIT, "Tài khoản chưa liên kết căn hộ.", 400)
        ticket = self.tickets.get_resident_ticket(resident_profile.unit_id, ticket_id)
        if ticket is None:
            raise DomainError(TICKET_NOT_FOUND, "Ticket không tồn tại.", 404)
        return ticket

    def cancel_ticket(self, user_id: UUID, resident_profile: ResidentProfile | None, ticket_id: UUID) -> Ticket:
        if resident_profile is None:
            raise DomainError(NO_ACTIVE_UNIT, "Tài khoản chưa liên kết căn hộ.", 400)
        try:
            ticket = self.tickets.get_resident_ticket(resident_profile.unit_id, ticket_id, lock=True)
            if ticket is None:
                raise DomainError(TICKET_NOT_FOUND, "Ticket không tồn tại.", 404)
            if ticket.status != TicketStatus.NEW:
                raise DomainError(INVALID_STATUS_TRANSITION, "Chỉ có thể hủy ticket ở trạng thái Mới.", 409)
            old = ticket.status
            ticket.status = TicketStatus.CANCELLED
            ticket.cancelled_at = datetime.now(UTC)
            ticket.version += 1
            self.tickets.append_status_history(
                ticket,
                from_status=old,
                to_status=TicketStatus.CANCELLED,
                changed_by=user_id,
                reason="Resident cancelled ticket.",
            )
            self.db.commit()
            return self.tickets.get_resident_ticket(resident_profile.unit_id, ticket.id) or ticket
        except Exception:
            self.db.rollback()
            raise

    def supplement(
        self,
        user_id: UUID,
        resident_profile: ResidentProfile | None,
        ticket_id: UUID,
        request: TicketSupplementRequest,
    ) -> Ticket:
        if resident_profile is None:
            raise DomainError(NO_ACTIVE_UNIT, "Tài khoản chưa liên kết căn hộ.", 400)
        try:
            ticket = self.tickets.get_resident_ticket(resident_profile.unit_id, ticket_id, lock=True)
            if ticket is None:
                raise DomainError(TICKET_NOT_FOUND, "Ticket không tồn tại.", 404)
            if ticket.status != TicketStatus.WAITING_RESIDENT_INFO:
                raise DomainError(INVALID_STATUS_TRANSITION, "Ticket không ở trạng thái chờ bổ sung thông tin.", 409)
            info_request = self.tickets.get_information_request(ticket.id, request.information_request_id, lock=True)
            if info_request is None or info_request.status != InformationRequestStatus.OPEN:
                raise DomainError(INFORMATION_REQUEST_NOT_FOUND, "Yêu cầu bổ sung không còn hiệu lực.", 404)
            sessions = self._lock_and_verify_upload_sessions(user_id, request.attachment_upload_ids)
            if request.description and request.description.strip():
                info_request.resident_response_text = request.description.strip()
            info_request.status = InformationRequestStatus.RESPONDED
            info_request.responded_at = datetime.now(UTC)
            self.tickets.create_attachments_from_upload_sessions(
                ticket.id,
                user_id,
                sessions,
                attachment_type=AttachmentType.RESIDENT_SUPPLEMENT,
            )
            self.tickets.mark_upload_sessions_consumed(sessions)
            old = ticket.status
            ticket.status = TicketStatus.NEW
            ticket.classification_status = ClassificationStatus.PROCESSING
            ticket.category_id = None
            ticket.priority = None
            ticket.severity = None
            ticket.red_flag_detected = False
            ticket.score_total = None
            ticket.sla_due_at = None
            ticket.version += 1
            self.tickets.append_status_history(
                ticket,
                from_status=old,
                to_status=TicketStatus.NEW,
                changed_by=user_id,
                reason="Resident supplied requested information.",
            )
            self.db.commit()
            return self.tickets.get_resident_ticket(resident_profile.unit_id, ticket.id) or ticket
        except Exception:
            self.db.rollback()
            raise

    def get_attachment_download_url(
        self,
        resident_profile: ResidentProfile | None,
        ticket_id: UUID,
        attachment_id: UUID,
    ) -> tuple[TicketAttachment, str, int]:
        ticket = self.get_ticket(resident_profile, ticket_id)
        attachment = self.tickets.get_attachment(ticket.id, attachment_id)
        if attachment is None:
            raise DomainError(ATTACHMENT_NOT_FOUND, "Attachment không tồn tại.", 404)
        signed_url = self.storage.create_signed_download_url(attachment.object_path)
        return attachment, signed_url, self.storage.settings.supabase_signed_download_ttl_seconds

    def _lock_and_verify_upload_sessions(
        self, owner_user_id: UUID, upload_ids: list[UUID]
    ) -> list[TicketAttachmentUploadSession]:
        if not upload_ids:
            return []
        sessions = self.tickets.lock_upload_sessions(upload_ids)
        by_id = {row.id: row for row in sessions}
        if set(by_id) != set(upload_ids):
            raise DomainError(INVALID_ATTACHMENT, "Upload session không hợp lệ.", 400)
        ordered = [by_id[upload_id] for upload_id in upload_ids]
        now = datetime.now(UTC)
        verified_at = now
        for session in ordered:
            if session.owner_user_id != owner_user_id:
                raise DomainError(INVALID_ATTACHMENT, "Upload session không hợp lệ.", 400)
            if session.status != "pending" or session.consumed_at is not None:
                raise DomainError(INVALID_ATTACHMENT, "Upload session đã được sử dụng.", 400)
            expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=UTC)
            if expires_at <= now:
                raise DomainError(INVALID_ATTACHMENT, "Upload session đã hết hạn.", 400)
            if not self.storage.is_owned_ticket_attachment_path(session.storage_path, owner_user_id):
                raise DomainError(INVALID_ATTACHMENT, "Upload session không hợp lệ.", 400)
            try:
                verified = self.storage.verify_uploaded_object(
                    session.storage_path,
                    expected_mime_type=session.mime_type,
                    expected_file_size=session.file_size,
                )
            except DomainError as exc:
                if exc.code == STORAGE_NOT_CONFIGURED:
                    raise
                raise
            verified_at = verified.verified_at
        self.tickets.mark_upload_sessions_verified(ordered, verified_at)
        return ordered
