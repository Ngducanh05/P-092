"""Ticket persistence operations for the Self Dev v2 workflow."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from src.database.models.attachment import TicketAttachment
from src.database.models.category import CategoryCatalog
from src.database.models.information_request import InformationRequest
from src.database.models.notification import Notification
from src.database.models.ticket import Ticket
from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession
from src.database.models.ticket_status_history import TicketStatusHistory
from src.models.enums import AttachmentType, Category, ClassificationStatus, ImageQualityStatus, Priority, TicketStatus
from src.services.storage_service import SIGNED_UPLOAD_EXPIRY_SECONDS


class TicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_ticket(
        self,
        *,
        reporter_user_id: UUID,
        source_unit_id: UUID,
        location_id: UUID,
        description: str | None,
    ) -> Ticket:
        now = datetime.now(UTC)
        ticket = Ticket(
            reporter_user_id=reporter_user_id,
            source_unit_id=source_unit_id,
            location_id=location_id,
            description=description.strip() if description else None,
            status=TicketStatus.NEW,
            classification_status=ClassificationStatus.PROCESSING,
            sla_started_at=now,
        )
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def append_status_history(
        self,
        ticket: Ticket,
        *,
        from_status: TicketStatus | None,
        to_status: TicketStatus,
        changed_by: UUID | None,
        reason: str | None,
    ) -> TicketStatusHistory:
        row = TicketStatusHistory(
            ticket_id=ticket.id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            reason=reason,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def create_upload_session(
        self,
        owner_user_id: UUID,
        storage_path: str,
        original_filename: str | None,
        mime_type: str,
        file_size: int,
    ) -> TicketAttachmentUploadSession:
        row = TicketAttachmentUploadSession(
            owner_user_id=owner_user_id,
            storage_path=storage_path,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size=file_size,
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(seconds=SIGNED_UPLOAD_EXPIRY_SECONDS),
        )
        self.db.add(row)
        self.db.flush()
        return row

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
        owner_user_id: UUID,
        upload_sessions: list[TicketAttachmentUploadSession],
        *,
        attachment_type: AttachmentType = AttachmentType.ISSUE_ORIGINAL,
    ) -> list[TicketAttachment]:
        rows = [
            TicketAttachment(
                ticket_id=ticket_id,
                attachment_type=attachment_type,
                storage_bucket="ticket-attachments",
                object_path=session.storage_path,
                mime_type=session.mime_type,
                size_bytes=session.file_size,
                uploaded_by=owner_user_id,
                image_quality_status=ImageQualityStatus.PENDING,
            )
            for session in upload_sessions
        ]
        self.db.add_all(rows)
        self.db.flush()
        return rows

    def mark_upload_sessions_verified(self, sessions: list[TicketAttachmentUploadSession], verified_at: datetime) -> None:
        for session in sessions:
            session.object_verified_at = verified_at
            session.updated_at = verified_at
        self.db.flush()

    def mark_upload_sessions_consumed(self, sessions: list[TicketAttachmentUploadSession]) -> None:
        now = datetime.now(UTC)
        for session in sessions:
            session.status = "consumed"
            session.consumed_at = now
            session.updated_at = now
        self.db.flush()

    def list_resident_tickets(
        self,
        source_unit_id: UUID,
        page: int,
        page_size: int,
        *,
        status: TicketStatus | None = None,
        category: Category | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[Ticket], int]:
        query = select(Ticket).where(Ticket.source_unit_id == source_unit_id)
        query = self._apply_filters(query, status=status, category=category, priority=None, classification_status=None,
                                    created_from=created_from, created_to=created_to)
        total = int(self.db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        items = list(
            self.db.scalars(
                query.options(
                    selectinload(Ticket.attachments),
                    joinedload(Ticket.category),
                    joinedload(Ticket.location),
                )
                .order_by(Ticket.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    def get_resident_ticket(self, source_unit_id: UUID, ticket_id: UUID, *, lock: bool = False) -> Ticket | None:
        query = (
            select(Ticket)
            .where(Ticket.id == ticket_id, Ticket.source_unit_id == source_unit_id)
            .options(
                selectinload(Ticket.attachments),
                selectinload(Ticket.status_history),
                joinedload(Ticket.category),
                joinedload(Ticket.location),
            )
        )
        if lock:
            query = query.with_for_update()
        return self.db.scalar(query)

    def list_coordinator_tickets(
        self,
        page: int,
        page_size: int,
        *,
        status: TicketStatus | None = None,
        category: Category | None = None,
        priority: Priority | None = None,
        classification_status: ClassificationStatus | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        search: str | None = None,
    ) -> tuple[list[Ticket], int]:
        query = self._apply_filters(
            select(Ticket),
            status=status,
            category=category,
            priority=priority,
            classification_status=classification_status,
            created_from=created_from,
            created_to=created_to,
        )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(Ticket.description.ilike(pattern))
        total = int(self.db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        priority_order = case(
            (Ticket.classification_status == ClassificationStatus.MANUAL_REVIEW, 0),
            (Ticket.priority == Priority.P3, 1),
            (Ticket.priority == Priority.P2, 2),
            (Ticket.priority == Priority.P1, 3),
            else_=4,
        )
        items = list(
            self.db.scalars(
                query.options(
                    selectinload(Ticket.attachments),
                    selectinload(Ticket.status_history),
                    selectinload(Ticket.ai_analysis_runs),
                    joinedload(Ticket.category),
                    joinedload(Ticket.location),
                )
                .order_by(priority_order, Ticket.created_at.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    def get_coordinator_ticket(self, ticket_id: UUID, *, lock: bool = False) -> Ticket | None:
        query = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.attachments),
                selectinload(Ticket.status_history),
                selectinload(Ticket.information_requests),
                selectinload(Ticket.ai_analysis_runs),
                joinedload(Ticket.category),
                joinedload(Ticket.location),
            )
        )
        if lock:
            query = query.with_for_update()
        return self.db.scalar(query)

    def get_attachment(self, ticket_id: UUID, attachment_id: UUID) -> TicketAttachment | None:
        return self.db.scalar(
            select(TicketAttachment).where(
                TicketAttachment.ticket_id == ticket_id,
                TicketAttachment.id == attachment_id,
            )
        )

    def get_information_request(self, ticket_id: UUID, request_id: UUID, *, lock: bool = False) -> InformationRequest | None:
        query = select(InformationRequest).where(
            InformationRequest.id == request_id,
            InformationRequest.ticket_id == ticket_id,
        )
        if lock:
            query = query.with_for_update()
        return self.db.scalar(query)

    def add_notification(self, notification: Notification) -> None:
        self.db.add(notification)
        self.db.flush()

    def _apply_filters(
        self,
        query,
        *,
        status,
        category,
        priority,
        classification_status,
        created_from,
        created_to,
    ):
        if status is not None:
            query = query.where(Ticket.status == status)
        if category is not None:
            query = query.join(CategoryCatalog, CategoryCatalog.id == Ticket.category_id).where(CategoryCatalog.code == category)
        if priority is not None:
            query = query.where(Ticket.priority == priority)
        if classification_status is not None:
            query = query.where(Ticket.classification_status == classification_status)
        if created_from is not None:
            query = query.where(Ticket.created_at >= created_from)
        if created_to is not None:
            query = query.where(Ticket.created_at <= created_to)
        return query
