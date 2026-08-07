"""Technician assignment domain business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models.attachment import TicketAttachment
from src.database.models.audit_log import AuditLog
from src.database.models.notification import Notification
from src.database.models.ticket_assignment import TicketAssignment
from src.database.models.ticket_status_history import TicketStatusHistory
from src.models.api.errors import (
    ASSIGNMENT_CONFLICT,
    ASSIGNMENT_NOT_FOUND,
    ATTACHMENT_NOT_FOUND,
    COMPLETION_EVIDENCE_REQUIRED,
    INVALID_ASSIGNMENT_TRANSITION,
    TECHNICIAN_NOT_FOUND,
    TECHNICIAN_UNAVAILABLE,
    TICKET_NOT_FOUND,
    TICKET_NOT_READY_FOR_ASSIGNMENT,
    UNABLE_REASON_REQUIRED,
    DomainError,
)
from src.models.enums import AssignmentStatus, TicketStatus
from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.ticket_repository import TicketRepository
from src.services.storage_service import StorageService

_ASSIGNABLE_TICKET_STATUSES = {TicketStatus.WAITING_ASSIGNMENT}
_ALLOWED_STATUS_TRANSITIONS: dict[AssignmentStatus, set[AssignmentStatus]] = {
    AssignmentStatus.ASSIGNED: {AssignmentStatus.UNABLE_TO_HANDLE},
    AssignmentStatus.ACCEPTED: {AssignmentStatus.IN_PROGRESS, AssignmentStatus.UNABLE_TO_HANDLE},
    AssignmentStatus.IN_PROGRESS: {AssignmentStatus.UNABLE_TO_HANDLE},
}


class AssignmentService:
    """Coordinate BQL assignment and Technician-owned workflow transitions."""

    def __init__(self, db: Session, storage_service: StorageService | None = None) -> None:
        self.db = db
        self.assignments = AssignmentRepository(db)
        self.tickets = TicketRepository(db)
        self.storage = storage_service

    def list_technicians(self, page: int, page_size: int):
        """Return active Technician profiles and their skills for BQL routing."""
        return self.assignments.list_active_available_technicians(page, page_size)

    def assign_ticket(
        self,
        ticket_id: UUID,
        technician_id: UUID,
        assigned_by_auth_user_id: UUID,
        assignment_note: str | None,
    ) -> TicketAssignment:
        """Assign one eligible ticket atomically and generate required evidence."""
        ticket = self.tickets.get_ticket_by_id_for_bql(ticket_id)
        if ticket is None:
            raise DomainError(TICKET_NOT_FOUND, "Ticket not found.", 404)
        if self.assignments.get_active_assignment_for_ticket(ticket_id) is not None:
            raise DomainError(ASSIGNMENT_CONFLICT, "Ticket already has an active assignment.", 409)
        if ticket.category is None:
            raise DomainError(
                TICKET_NOT_READY_FOR_ASSIGNMENT,
                "Ticket has no category and cannot be assigned.",
                422,
            )
        if ticket.status not in _ASSIGNABLE_TICKET_STATUSES:
            raise DomainError(
                TICKET_NOT_READY_FOR_ASSIGNMENT,
                "Ticket is not in a state that can be assigned.",
                409,
            )

        technician = self.assignments.get_technician_with_skills(technician_id)
        if technician is None:
            raise DomainError(TECHNICIAN_NOT_FOUND, "Technician not found.", 404)
        if not technician.is_active or not technician.is_available:
            raise DomainError(TECHNICIAN_UNAVAILABLE, "Technician is not active or available.", 422)
        if not self.assignments.skill_matches_category(technician_id, ticket.category):
            raise DomainError(
                TECHNICIAN_UNAVAILABLE,
                "Technician does not have a skill matching the ticket category.",
                422,
            )

        try:
            assignment = self.assignments.create_assignment(
                ticket_id=ticket_id,
                technician_id=technician_id,
                assigned_by_auth_user_id=assigned_by_auth_user_id,
                assignment_note=_clean_optional_text(assignment_note),
            )
            old_status = ticket.status
            ticket.status = TicketStatus.ASSIGNED
            ticket.updated_at = datetime.now(UTC)

            self.db.add(
                TicketStatusHistory(
                    ticket_id=ticket_id,
                    from_status=old_status,
                    to_status=TicketStatus.ASSIGNED,
                    changed_by_auth_user_id=assigned_by_auth_user_id,
                    change_reason="Assigned to technician by BQL staff.",
                )
            )
            self.db.add_all(
                [
                    Notification(
                        recipient_auth_user_id=technician_id,
                        ticket_id=ticket_id,
                        event_type="ticket_assigned",
                        title="New ticket assigned",
                        body="A new maintenance ticket has been assigned to you.",
                    ),
                    Notification(
                        recipient_auth_user_id=ticket.resident_id,
                        ticket_id=ticket_id,
                        event_type="technician_assigned",
                        title="Technician assigned",
                        body="A technician has been assigned to your maintenance ticket.",
                    ),
                ]
            )
            self.db.add(
                AuditLog(
                    actor_auth_user_id=assigned_by_auth_user_id,
                    entity_type="ticket_assignment",
                    entity_id=assignment.id,
                    action="assign",
                    old_values={"ticket_status": old_status.value},
                    new_values={
                        "ticket_id": str(ticket_id),
                        "technician_id": str(technician_id),
                        "ticket_status": TicketStatus.ASSIGNED.value,
                    },
                )
            )
            self.db.commit()
            return self._refresh_with_ticket(assignment)
        except DomainError:
            self.db.rollback()
            raise
        except IntegrityError as exc:
            self.db.rollback()
            raise DomainError(ASSIGNMENT_CONFLICT, "Assignment conflict detected.", 409) from exc
        except Exception:
            self.db.rollback()
            raise

    def list_own_assignments(self, technician_id: UUID) -> list[TicketAssignment]:
        """Return only active work owned by the authenticated Technician."""
        return self.assignments.list_active_assignments_for_technician(technician_id)

    def get_own_assignment(self, assignment_id: UUID, technician_id: UUID) -> TicketAssignment:
        """Return one active owned assignment or a masked 404."""
        return self._get_owned_assignment(assignment_id, technician_id, lock=False)


    def get_own_attachment_download_url(
        self,
        assignment_id: UUID,
        attachment_id: UUID,
        technician_id: UUID,
    ) -> tuple[TicketAttachment, str, int]:
        """Sign an attachment only through an active assignment owned by the Technician."""
        assignment = self._get_owned_assignment(assignment_id, technician_id, lock=False)
        attachment = self.tickets.get_attachment_for_ticket(assignment.ticket_id, attachment_id)
        if attachment is None:
            raise DomainError(ATTACHMENT_NOT_FOUND, "Attachment not found.", 404)
        storage = self.storage or StorageService()
        signed_url = storage.create_signed_download_url(attachment.file_url)
        return attachment, signed_url, storage.settings.supabase_signed_download_ttl_seconds

    def accept_assignment(self, assignment_id: UUID, technician_id: UUID) -> TicketAssignment:
        """Acknowledge an assignment without changing the parent ticket status."""
        assignment = self._get_owned_assignment(assignment_id, technician_id, lock=True)
        if assignment.status != AssignmentStatus.ASSIGNED:
            raise DomainError(
                INVALID_ASSIGNMENT_TRANSITION,
                f"Cannot accept an assignment with status '{assignment.status.value}'.",
                422,
            )

        try:
            now = datetime.now(UTC)
            assignment.status = AssignmentStatus.ACCEPTED
            assignment.accepted_at = now
            assignment.updated_at = now
            self._add_assignment_audit(
                assignment,
                technician_id,
                action="accept",
                old_status=AssignmentStatus.ASSIGNED,
                new_status=AssignmentStatus.ACCEPTED,
            )
            self.db.commit()
            return self._refresh_with_ticket(assignment)
        except Exception:
            self.db.rollback()
            raise

    def update_assignment_status(
        self,
        assignment_id: UUID,
        technician_id: UUID,
        requested_status: AssignmentStatus,
        unable_reason: str | None,
        work_note: str | None = None,
    ) -> TicketAssignment:
        """Apply an allowed Technician-owned assignment transition atomically."""
        assignment = self._get_owned_assignment(assignment_id, technician_id, lock=True)

        # Completion remains blocked until Technician-owned, verified upload sessions
        # exist; checking ownership first preserves the masked-404 boundary.
        if requested_status == AssignmentStatus.COMPLETED:
            raise DomainError(
                COMPLETION_EVIDENCE_REQUIRED,
                "Completion requires secure photo evidence; this transition is not yet supported.",
                422,
            )

        allowed = _ALLOWED_STATUS_TRANSITIONS.get(assignment.status, set())
        if requested_status not in allowed:
            raise DomainError(
                INVALID_ASSIGNMENT_TRANSITION,
                f"Cannot transition from '{assignment.status.value}' to '{requested_status.value}'.",
                422,
            )

        cleaned_reason = _clean_optional_text(unable_reason)
        if requested_status == AssignmentStatus.UNABLE_TO_HANDLE and not cleaned_reason:
            raise DomainError(UNABLE_REASON_REQUIRED, "unable_reason is required for unable_to_handle.", 422)

        try:
            now = datetime.now(UTC)
            old_assignment_status = assignment.status
            assignment.status = requested_status
            assignment.updated_at = now
            cleaned_work_note = _clean_optional_text(work_note)
            if cleaned_work_note is not None:
                assignment.work_note = cleaned_work_note

            ticket = assignment.ticket
            if requested_status == AssignmentStatus.IN_PROGRESS:
                if ticket.status != TicketStatus.ASSIGNED:
                    raise DomainError(
                        INVALID_ASSIGNMENT_TRANSITION,
                        "Parent ticket is not in the assigned state.",
                        409,
                    )
                assignment.started_at = now
                self._transition_ticket(
                    ticket=ticket,
                    target=TicketStatus.IN_PROGRESS,
                    actor_auth_user_id=technician_id,
                    reason="Technician started work.",
                )
                self.db.add(
                    Notification(
                        recipient_auth_user_id=ticket.resident_id,
                        ticket_id=ticket.id,
                        event_type="ticket_in_progress",
                        title="Ticket in progress",
                        body="A technician has started working on your maintenance ticket.",
                    )
                )

            elif requested_status == AssignmentStatus.UNABLE_TO_HANDLE:
                assignment.unable_reason = cleaned_reason
                assignment.ended_at = now
                assignment.is_active = False
                self._transition_ticket(
                    ticket=ticket,
                    target=TicketStatus.WAITING_ASSIGNMENT,
                    actor_auth_user_id=technician_id,
                    reason="Technician unable to handle; returned to assignment queue.",
                )
                self.db.add(
                    Notification(
                        recipient_auth_user_id=ticket.resident_id,
                        ticket_id=ticket.id,
                        event_type="ticket_waiting_reassignment",
                        title="Ticket awaiting reassignment",
                        body="Your maintenance ticket is being reassigned to another technician.",
                    )
                )

            self._add_assignment_audit(
                assignment,
                technician_id,
                action="status_update",
                old_status=old_assignment_status,
                new_status=requested_status,
            )
            self.db.commit()
            return self._refresh_with_ticket(assignment)
        except DomainError:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

    def _get_owned_assignment(
        self,
        assignment_id: UUID,
        technician_id: UUID,
        *,
        lock: bool,
    ) -> TicketAssignment:
        assignment = self.assignments.get_assignment_for_technician(
            assignment_id,
            technician_id,
            lock=lock,
        )
        if assignment is None:
            raise DomainError(ASSIGNMENT_NOT_FOUND, "Assignment not found.", 404)
        return assignment

    def _transition_ticket(
        self,
        *,
        ticket,
        target: TicketStatus,
        actor_auth_user_id: UUID,
        reason: str,
    ) -> None:
        old_status = ticket.status
        ticket.status = target
        ticket.updated_at = datetime.now(UTC)
        self.db.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=old_status,
                to_status=target,
                changed_by_auth_user_id=actor_auth_user_id,
                change_reason=reason,
            )
        )

    def _add_assignment_audit(
        self,
        assignment: TicketAssignment,
        actor_auth_user_id: UUID,
        *,
        action: str,
        old_status: AssignmentStatus,
        new_status: AssignmentStatus,
    ) -> None:
        self.db.add(
            AuditLog(
                actor_auth_user_id=actor_auth_user_id,
                entity_type="ticket_assignment",
                entity_id=assignment.id,
                action=action,
                old_values={"assignment_status": old_status.value},
                new_values={"assignment_status": new_status.value},
            )
        )

    def _refresh_with_ticket(self, assignment: TicketAssignment) -> TicketAssignment:
        self.db.refresh(assignment)
        _ = assignment.ticket
        return assignment


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
