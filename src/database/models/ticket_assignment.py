"""Ticket assignment persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import AssignmentStatus

if TYPE_CHECKING:
    from src.database.models.technician_profile import TechnicianProfile
    from src.database.models.ticket import Ticket


def enum_values(enum_class: type[AssignmentStatus]) -> list[str]:
    """Return stable persisted values for string enums."""
    return [member.value for member in enum_class]


class TicketAssignment(Base):
    """Work assignment linking a ticket to a technician.

    At most one row per ticket may be active. ``assigned_by_auth_user_id`` holds
    the assigning BQL Supabase Auth UUID so assignment history survives profile
    edits without a permanent ``tickets.bql_id`` column.
    """

    __tablename__ = "ticket_assignments"
    __table_args__ = (
        CheckConstraint(
            "status <> 'unable_to_handle' OR (unable_reason IS NOT NULL AND length(trim(unable_reason)) > 0)",
            name="ck_ticket_assignments_unable_reason_required",
        ),
        Index("ix_ticket_assignments_technician_active", "technician_id", "is_active"),
        Index("ix_ticket_assignments_ticket_assigned_at", "ticket_id", "assigned_at"),
        Index(
            "uq_ticket_assignments_one_active_per_ticket",
            "ticket_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    technician_id: Mapped[UUID] = mapped_column(
        ForeignKey("technician_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by_auth_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus, name="assignment_status_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
        default=AssignmentStatus.ASSIGNED,
        server_default=AssignmentStatus.ASSIGNED.value,
    )
    assignment_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    unable_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    work_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    ticket: Mapped[Ticket] = relationship(back_populates="assignments")
    technician: Mapped[TechnicianProfile] = relationship(back_populates="assignments")
