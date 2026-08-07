"""Ticket persistence operations."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from src.database.models.attachment import TicketAttachment
from src.database.models.resident_unit_membership import ResidentUnitMembership
from src.database.models.ticket import Ticket
from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession
from src.database.models.ticket_status_history import TicketStatusHistory
from src.models.enums import Category, Priority, TicketStatus
from src.services.storage_service import SIGNED_UPLOAD_EXPIRY_SECONDS


class TicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_ticket(self, resident_id: UUID, unit_id: UUID, title: str, description: str, location: str | None) -> Ticket:
        ticket = Ticket(
            resident_id=resident_id,
            unit_id=unit_id,
            title=title,
            description=description,
            location_description=location,
            status=TicketStatus.NEW,
        )
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def create_initial_status_history(self, ticket_id: UUID, changed_by_auth_user_id: UUID) -> TicketStatusHistory:
        history = TicketStatusHistory(
            ticket_id=ticket_id,
            from_status=None,
            to_status=TicketStatus.NEW,
            changed_by_auth_user_id=changed_by_auth_user_id,
            change_reason="Ticket created by resident.",
        )
        self.db.add(history)
        self.db.flush()
        return history

    def create_upload_session(
        self,
        resident_id: UUID,
        storage_path: str,
        original_filename: str | None,
        mime_type: str,
        file_size: int,
    ) -> TicketAttachmentUploadSession:
        upload_session = TicketAttachmentUploadSession(
            resident_id=resident_id,
            storage_path=storage_path,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size=file_size,
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(seconds=SIGNED_UPLOAD_EXPIRY_SECONDS),
        )
        self.db.add(upload_session)
        self.db.flush()
        return upload_session

    def lock_upload_sessions(self, upload_ids: list[UUID]) -> list[TicketAttachmentUploadSession]:
        if not upload_ids:
            return []
        return list(
            self.db.scalars(
                select(TicketAttachmentUploadSession)
                .where(TicketAttachmentUploadSession.id.in_(upload_ids))
                .with_for_update()
            )
        )

    def create_attachments_from_upload_sessions(
        self,
        ticket_id: UUID,
        upload_sessions: list[TicketAttachmentUploadSession],
    ) -> list[TicketAttachment]:
        attachments = [
            TicketAttachment(
                ticket_id=ticket_id,
                file_url=upload_session.storage_path,
                file_type=self._file_type_for_mime(upload_session.mime_type),
                mime_type=upload_session.mime_type,
                file_size=upload_session.file_size,
            )
            for upload_session in upload_sessions
        ]
        self.db.add_all(attachments)
        self.db.flush()
        return attachments

    def mark_upload_sessions_consumed(self, upload_sessions: list[TicketAttachmentUploadSession]) -> None:
        now = datetime.now(UTC)
        for upload_session in upload_sessions:
            upload_session.status = "consumed"
            upload_session.consumed_at = now
            upload_session.updated_at = now
        self.db.flush()

    def mark_upload_sessions_verified(
        self,
        upload_sessions: list[TicketAttachmentUploadSession],
        verified_at: datetime,
    ) -> None:
        for upload_session in upload_sessions:
            upload_session.object_verified_at = verified_at
            upload_session.updated_at = verified_at
        self.db.flush()

    def list_resident_accessible_tickets(
        self,
        resident_id: UUID,
        page: int,
        page_size: int,
        status: TicketStatus | None = None,
        category: Category | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[Ticket], int]:
        query = self._resident_query(resident_id)
        query = self._apply_filters(query, status, category, None, created_from, created_to)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = list(
            self.db.scalars(
                query.options(selectinload(Ticket.attachments))
                .order_by(Ticket.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, int(total)

    def get_resident_accessible_ticket(self, resident_id: UUID, ticket_id: UUID) -> Ticket | None:
        return self.db.scalar(
            self._resident_query(resident_id)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.attachments))
        )

    def list_bql_tickets(
        self,
        page: int,
        page_size: int,
        status: TicketStatus | None = None,
        category: Category | None = None,
        priority: Priority | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[Ticket], int]:
        query = self._apply_filters(select(Ticket), status, category, priority, created_from, created_to)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        priority_order = case(
            (Ticket.priority == Priority.P3, 1),
            (Ticket.priority == Priority.P2, 2),
            (Ticket.priority == Priority.P1, 3),
            (Ticket.priority == Priority.P4, 4),
            else_=5,
        )
        items = list(
            self.db.scalars(
                query.options(selectinload(Ticket.attachments))
                .order_by(priority_order, Ticket.created_at.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, int(total)

    def get_ticket_by_id_for_bql(self, ticket_id: UUID) -> Ticket | None:
        return self.db.scalar(select(Ticket).where(Ticket.id == ticket_id).options(selectinload(Ticket.attachments)))

    def get_attachment_for_ticket(self, ticket_id: UUID, attachment_id: UUID) -> TicketAttachment | None:
        return self.db.scalar(
            select(TicketAttachment).where(TicketAttachment.ticket_id == ticket_id, TicketAttachment.id == attachment_id)
        )

    def _resident_query(self, resident_id: UUID):
        return (
            select(Ticket)
            .join(ResidentUnitMembership, ResidentUnitMembership.unit_id == Ticket.unit_id)
            .where(ResidentUnitMembership.resident_id == resident_id, ResidentUnitMembership.is_active.is_(True))
        )

    def _apply_filters(self, query, status, category, priority, created_from, created_to):
        if status is not None:
            query = query.where(Ticket.status == status)
        if category is not None:
            query = query.where(Ticket.category == category)
        if priority is not None:
            query = query.where(Ticket.priority == priority)
        if created_from is not None:
            query = query.where(Ticket.created_at >= created_from)
        if created_to is not None:
            query = query.where(Ticket.created_at <= created_to)
        return query

    def _file_type_for_mime(self, mime_type: str) -> str:
        if mime_type.startswith("image/"):
            return "image"
        return "private_storage"
