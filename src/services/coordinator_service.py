"""Coordinator business workflow from Self_Dev_Docs v2."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models.audit_log import AuditLog
from src.database.models.category import CategoryCatalog
from src.database.models.information_request import InformationRequest
from src.database.models.location import Location
from src.database.models.notification import Notification
from src.database.models.resident_profile import ResidentProfile
from src.database.models.scoring_rule_version import ScoringRuleVersion
from src.database.models.ticket import Ticket
from src.models.api.coordinator import ClassificationOverrideRequest, ManualReviewResolveRequest
from src.models.api.errors import (
    CATEGORY_REQUIRED,
    INVALID_STATUS_TRANSITION,
    P0_REVIEW_REQUIRED,
    TICKET_NOT_FOUND,
    DomainError,
)
from src.models.enums import (
    Category,
    ClassificationStatus,
    InformationRequestStatus,
    NotificationChannel,
    NotificationStatus,
    Priority,
    TicketStatus,
)
from src.repositories.catalog_repository import CatalogRepository
from src.repositories.ticket_repository import TicketRepository
from src.request_context import request_id_context
from src.services.scoring_service import ScoringService


class CoordinatorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tickets = TicketRepository(db)
        self.catalog = CatalogRepository(db)
        active_rule = db.scalar(select(ScoringRuleVersion).where(ScoringRuleVersion.is_active.is_(True)))
        self.scoring_rule_version_id = active_rule.id if active_rule else None
        self.scoring = ScoringService(active_rule.config if active_rule else None)

    def list_tickets(self, page: int, page_size: int, **filters):
        return self.tickets.list_coordinator_tickets(page, page_size, **filters)

    def get_ticket(self, ticket_id: UUID) -> Ticket:
        ticket = self.tickets.get_coordinator_ticket(ticket_id)
        if ticket is None:
            raise DomainError(TICKET_NOT_FOUND, "Ticket không tồn tại.", 404)
        return ticket

    def resolve_manual_review(
        self,
        coordinator_user_id: UUID,
        ticket_id: UUID,
        request: ManualReviewResolveRequest,
    ) -> Ticket:
        try:
            ticket = self._locked(ticket_id)
            if ticket.classification_status != ClassificationStatus.MANUAL_REVIEW:
                raise DomainError(P0_REVIEW_REQUIRED, "Ticket không ở trạng thái P0/manual review.", 409)
            category = self.catalog.get_category(request.category_id)
            if category is None:
                raise DomainError(CATEGORY_REQUIRED, "Category không hợp lệ.", 400)
            if ticket.severity is None:
                raise DomainError(P0_REVIEW_REQUIRED, "AI chưa cung cấp Severity để tính lại điểm.", 409)

            # When the Coordinator explicitly says the image or text prediction
            # is the trusted source, the selected Category must actually exist
            # in that source's latest AI output. OTHER intentionally allows an
            # independent human Category choice.
            if ticket.ai_analysis_runs:
                latest_run = max(ticket.ai_analysis_runs, key=lambda item: item.run_number)
                selected_code = category.code.value
                if request.resolution_source.value == "IMAGE":
                    if not latest_run.image_categories or selected_code not in latest_run.image_categories:
                        raise DomainError(CATEGORY_REQUIRED, "Category đã chọn không thuộc kết quả phân loại từ ảnh.", 400)
                elif request.resolution_source.value == "TEXT":
                    if selected_code not in latest_run.text_categories:
                        raise DomainError(CATEGORY_REQUIRED, "Category đã chọn không thuộc kết quả phân loại từ text.", 400)

            before = self._classification_snapshot(ticket)
            ticket.category_id = category.id
            ticket.classification_status = ClassificationStatus.RESOLVED
            self._apply_scoring(ticket, category)
            ticket.version += 1
            after = self._classification_snapshot(ticket)
            after["resolution_source"] = request.resolution_source.value
            self._audit(
                coordinator_user_id,
                "RESOLVE_MANUAL_REVIEW",
                ticket,
                before,
                after,
                request.reason,
            )
            self.db.commit()
            return self.get_ticket(ticket.id)
        except Exception:
            self.db.rollback()
            raise

    def request_information(
        self,
        coordinator_user_id: UUID,
        ticket_id: UUID,
        message: str,
    ) -> Ticket:
        try:
            ticket = self._locked(ticket_id)
            if ticket.status != TicketStatus.NEW:
                raise DomainError(INVALID_STATUS_TRANSITION, "Chỉ ticket Mới mới có thể yêu cầu bổ sung thông tin.", 409)
            old = ticket.status
            row = InformationRequest(
                ticket_id=ticket.id,
                requested_by=coordinator_user_id,
                request_message=message,
                status=InformationRequestStatus.OPEN,
            )
            self.db.add(row)
            self.db.flush()
            ticket.status = TicketStatus.WAITING_RESIDENT_INFO
            ticket.version += 1
            self.tickets.append_status_history(
                ticket,
                from_status=old,
                to_status=TicketStatus.WAITING_RESIDENT_INFO,
                changed_by=coordinator_user_id,
                reason="Coordinator requested resident information.",
            )
            self._notify_unit(
                ticket,
                "INFORMATION_REQUESTED",
                "BQL yêu cầu bổ sung thông tin",
                message,
            )
            self._audit(
                coordinator_user_id,
                "REQUEST_INFORMATION",
                ticket,
                {"status": old.value},
                {"status": ticket.status.value, "information_request_id": str(row.id)},
                message,
            )
            self.db.commit()
            return self.get_ticket(ticket.id)
        except Exception:
            self.db.rollback()
            raise

    def approve(self, coordinator_user_id: UUID, ticket_id: UUID) -> Ticket:
        try:
            ticket = self._locked(ticket_id)
            if ticket.status != TicketStatus.NEW:
                raise DomainError(INVALID_STATUS_TRANSITION, "Chỉ ticket Mới mới có thể được duyệt.", 409)
            if ticket.classification_status == ClassificationStatus.MANUAL_REVIEW:
                raise DomainError(P0_REVIEW_REQUIRED, "Phải xử lý P0 trước khi duyệt ticket.", 409)
            if (
                ticket.classification_status != ClassificationStatus.RESOLVED
                or ticket.category_id is None
                or ticket.priority is None
            ):
                raise DomainError(CATEGORY_REQUIRED, "Ticket chưa có Category/Priority hợp lệ.", 409)
            return self._transition(
                coordinator_user_id,
                ticket,
                TicketStatus.APPROVED,
                action="APPROVE_TICKET",
                notification_title="Phản ánh đã được duyệt",
                notification_body="Ban quản lý đã duyệt phản ánh của bạn.",
            )
        except Exception:
            self.db.rollback()
            raise

    def start(self, coordinator_user_id: UUID, ticket_id: UUID) -> Ticket:
        try:
            ticket = self._locked(ticket_id)
            if ticket.status != TicketStatus.APPROVED:
                raise DomainError(INVALID_STATUS_TRANSITION, "Chỉ ticket Đã duyệt mới có thể bắt đầu xử lý.", 409)
            return self._transition(
                coordinator_user_id,
                ticket,
                TicketStatus.IN_PROGRESS,
                action="START_TICKET",
                notification_title="Phản ánh đang được xử lý",
                notification_body="Ban quản lý đã bắt đầu xử lý phản ánh của bạn.",
            )
        except Exception:
            self.db.rollback()
            raise

    def complete(self, coordinator_user_id: UUID, ticket_id: UUID) -> Ticket:
        try:
            ticket = self._locked(ticket_id)
            if ticket.status != TicketStatus.IN_PROGRESS:
                raise DomainError(INVALID_STATUS_TRANSITION, "Chỉ ticket Đang xử lý mới có thể hoàn thành.", 409)
            return self._transition(
                coordinator_user_id,
                ticket,
                TicketStatus.COMPLETED,
                action="COMPLETE_TICKET",
                notification_title="Phản ánh đã hoàn thành",
                notification_body="Ban quản lý đã hoàn thành xử lý phản ánh của bạn.",
            )
        except Exception:
            self.db.rollback()
            raise

    def unresolvable(self, coordinator_user_id: UUID, ticket_id: UUID) -> Ticket:
        try:
            ticket = self._locked(ticket_id)
            if ticket.status != TicketStatus.IN_PROGRESS:
                raise DomainError(INVALID_STATUS_TRANSITION, "Chỉ ticket Đang xử lý mới có thể đánh dấu không xử lý được.", 409)
            return self._transition(
                coordinator_user_id,
                ticket,
                TicketStatus.UNRESOLVABLE,
                action="MARK_UNRESOLVABLE",
                notification_title="Phản ánh chưa thể xử lý",
                notification_body="Ban quản lý đã cập nhật phản ánh thành Không xử lý được.",
            )
        except Exception:
            self.db.rollback()
            raise

    def override_classification(
        self,
        coordinator_user_id: UUID,
        ticket_id: UUID,
        request: ClassificationOverrideRequest,
    ) -> Ticket:
        try:
            ticket = self._locked(ticket_id)
            before = self._classification_snapshot(ticket)
            if request.category_id is not None:
                category = self.catalog.get_category(request.category_id)
                if category is None:
                    raise DomainError(CATEGORY_REQUIRED, "Category không hợp lệ.", 400)
                if ticket.severity is None:
                    raise DomainError(CATEGORY_REQUIRED, "Ticket chưa có Severity để tính lại Priority.", 409)
                ticket.category_id = category.id
                ticket.classification_status = ClassificationStatus.RESOLVED
                self._apply_scoring(ticket, category)
            if request.priority is not None:
                ticket.priority = Priority.P3 if ticket.red_flag_detected else request.priority
                self._recalculate_sla(ticket)
            ticket.version += 1
            self._audit(
                coordinator_user_id,
                "OVERRIDE_CLASSIFICATION",
                ticket,
                before,
                self._classification_snapshot(ticket),
                request.reason,
            )
            self.db.commit()
            return self.get_ticket(ticket.id)
        except Exception:
            self.db.rollback()
            raise

    def list_audit_logs(
        self,
        *,
        actor_user_id: UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        created_from=None,
        created_to=None,
        limit: int = 100,
    ) -> list[AuditLog]:
        query = select(AuditLog)
        if actor_user_id is not None:
            query = query.where(AuditLog.actor_user_id == actor_user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(AuditLog.entity_id == entity_id)
        if created_from is not None:
            query = query.where(AuditLog.created_at >= created_from)
        if created_to is not None:
            query = query.where(AuditLog.created_at <= created_to)
        return list(self.db.scalars(query.order_by(AuditLog.created_at.desc()).limit(limit)))

    def tickets_summary(self) -> dict[str, object]:
        total = int(self.db.scalar(select(func.count(Ticket.id))) or 0)
        status_rows = self.db.execute(select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)).all()
        priority_rows = self.db.execute(select(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority)).all()
        category_rows = self.db.execute(
            select(CategoryCatalog.code, func.count(Ticket.id))
            .join(Ticket, Ticket.category_id == CategoryCatalog.id)
            .group_by(CategoryCatalog.code)
        ).all()
        return {
            "total": total,
            "by_status": {status.value: int(count) for status, count in status_rows},
            "by_priority": {priority.value: int(count) for priority, count in priority_rows if priority is not None},
            "by_category": {category.value: int(count) for category, count in category_rows},
        }

    def sla_performance(self) -> dict[str, object]:
        completed = list(
            self.db.scalars(select(Ticket).where(Ticket.status == TicketStatus.COMPLETED, Ticket.completed_at.is_not(None)))
        )
        on_time = sum(1 for ticket in completed if ticket.sla_due_at and ticket.completed_at <= ticket.sla_due_at)
        total = len(completed)
        return {
            "completed_total": total,
            "completed_on_time": on_time,
            "compliance_rate": (on_time / total) if total else None,
        }

    def _locked(self, ticket_id: UUID) -> Ticket:
        ticket = self.tickets.get_coordinator_ticket(ticket_id, lock=True)
        if ticket is None:
            raise DomainError(TICKET_NOT_FOUND, "Ticket không tồn tại.", 404)
        return ticket

    def _apply_scoring(self, ticket: Ticket, category: CategoryCatalog) -> None:
        location = ticket.location
        density_count = self._density_count(ticket, category)
        result = self.scoring.calculate(
            category=category.code,
            severity=ticket.severity,
            location_type_code=location.location_type.code if location else None,
            density_count=density_count,
            red_flag_detected=ticket.red_flag_detected,
            priority_ceiling=category.priority_ceiling,
        )
        ticket.score_total = result.score_total
        ticket.priority = result.priority_final
        self._recalculate_sla(ticket)

    def _density_count(self, ticket: Ticket, category: CategoryCatalog) -> int:
        if category.code not in {Category.WATER_LEAK, Category.ELECTRICAL_SHORT}:
            return 1
        if ticket.location is None:
            return 1
        current_floor = ticket.location.floor
        window_start = ticket.created_at - timedelta(days=3)
        query = (
            select(func.count(func.distinct(Ticket.source_unit_id)))
            .join(Location, Location.id == Ticket.location_id)
            .join(CategoryCatalog, CategoryCatalog.id == Ticket.category_id)
            .where(
                CategoryCatalog.code == category.code,
                Ticket.created_at >= window_start,
                Location.building_id == ticket.location.building_id,
            )
        )
        # adjacency_index is defined on Floor; joining through relationship via floor_id keeps this backend-only.
        from src.database.models.floor import Floor

        query = query.join(Floor, Floor.id == Location.floor_id).where(
            Floor.adjacency_index.between(current_floor.adjacency_index - 1, current_floor.adjacency_index + 1)
        )
        return max(1, int(self.db.scalar(query) or 0))

    def _recalculate_sla(self, ticket: Ticket) -> None:
        if ticket.priority is None:
            ticket.sla_due_at = None
            return
        started = ticket.sla_started_at or ticket.created_at
        ticket.sla_started_at = started
        ticket.sla_due_at = started + self.scoring.sla_duration[ticket.priority]

    def _transition(
        self,
        coordinator_user_id: UUID,
        ticket: Ticket,
        to_status: TicketStatus,
        *,
        action: str,
        notification_title: str,
        notification_body: str,
    ) -> Ticket:
        old = ticket.status
        now = datetime.now(UTC)
        ticket.status = to_status
        ticket.version += 1
        if to_status == TicketStatus.APPROVED:
            ticket.approved_at = now
        elif to_status == TicketStatus.IN_PROGRESS:
            ticket.started_at = now
        elif to_status == TicketStatus.COMPLETED:
            ticket.completed_at = now
        self.tickets.append_status_history(
            ticket,
            from_status=old,
            to_status=to_status,
            changed_by=coordinator_user_id,
            reason=action,
        )
        self._notify_unit(ticket, action, notification_title, notification_body)
        self._audit(
            coordinator_user_id,
            action,
            ticket,
            {"status": old.value},
            {"status": to_status.value},
            None,
        )
        self.db.commit()
        return self.get_ticket(ticket.id)

    def _notify_unit(self, ticket: Ticket, event: str, title: str, body: str) -> None:
        recipients = list(
            self.db.scalars(select(ResidentProfile.user_id).where(ResidentProfile.unit_id == ticket.source_unit_id))
        )
        for user_id in recipients:
            self.db.add(
                Notification(
                    recipient_user_id=user_id,
                    ticket_id=ticket.id,
                    notification_type=event,
                    channel=NotificationChannel.IN_APP,
                    title=title,
                    body=body,
                    payload={"ticket_id": str(ticket.id), "status": ticket.status.value},
                    status=NotificationStatus.PENDING,
                )
            )

    def _audit(
        self,
        actor_user_id: UUID,
        action: str,
        ticket: Ticket,
        before_data: dict[str, object] | None,
        after_data: dict[str, object] | None,
        reason: str | None,
    ) -> None:
        self.db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                actor_role="COORDINATOR",
                action=action,
                entity_type="TICKET",
                entity_id=ticket.id,
                before_data=before_data,
                after_data=after_data,
                reason=reason,
                request_id=UUID(request_id) if (request_id := request_id_context.get()) else None,
            )
        )

    def _classification_snapshot(self, ticket: Ticket) -> dict[str, object]:
        return {
            "category_id": str(ticket.category_id) if ticket.category_id else None,
            "priority": ticket.priority.value if ticket.priority else None,
            "classification_status": ticket.classification_status.value,
            "score_total": float(ticket.score_total) if ticket.score_total is not None else None,
        }
