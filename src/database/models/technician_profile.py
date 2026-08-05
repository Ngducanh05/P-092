"""Technician operational profile persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.technician_skill import TechnicianSkill
    from src.database.models.ticket_assignment import TicketAssignment
    from src.database.models.user import User


class TechnicianProfile(Base):
    """Technician-specific operational state for a user account."""

    __tablename__ = "technician_profiles"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="technician_profile")
    skills: Mapped[list[TechnicianSkill]] = relationship(
        back_populates="technician",
        cascade="all, delete-orphan",
    )
    assigned_ticket_records: Mapped[list[TicketAssignment]] = relationship(
        back_populates="technician_profile",
        foreign_keys="TicketAssignment.technician_id",
    )
