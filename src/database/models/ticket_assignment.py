"""Ticket assignment history persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.technician_profile import TechnicianProfile
    from src.database.models.ticket import Ticket
    from src.database.models.user import User


class TicketAssignment(Base):
    """Historical coordinator assignment of a ticket to a technician."""

    __tablename__ = "ticket_assignments"
    __table_args__ = (
        Index("ix_ticket_assignments_ticket_assigned_at", "ticket_id", "assigned_at"),
        Index("ix_ticket_assignments_technician_active", "technician_id", "is_active"),
        Index(
            "uq_ticket_assignments_one_active_per_ticket",
            "ticket_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    technician_id: Mapped[UUID] = mapped_column(
        ForeignKey("technician_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    technician: Mapped[User] = relationship(
        back_populates="assigned_ticket_records",
        foreign_keys=[technician_id],
        primaryjoin="User.id == foreign(TicketAssignment.technician_id)",
        viewonly=True,
    )
    technician_profile: Mapped[TechnicianProfile] = relationship(
        back_populates="assigned_ticket_records",
        foreign_keys=[technician_id],
    )
    assigned_by_user: Mapped[User] = relationship(
        back_populates="coordinator_assignment_records",
        foreign_keys=[assigned_by_user_id],
    )
