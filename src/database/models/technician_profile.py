"""Technician business profile persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.technician_skill import TechnicianSkill
    from src.database.models.ticket_assignment import TicketAssignment


class TechnicianProfile(Base):
    """Technician profile linked to a Supabase Auth user ID.

    ``id`` is both the primary key and the foreign key to ``auth.users.id``. A
    single Auth identity may hold at most one actor profile; exclusivity across
    residents, bql_staff, and technician_profiles is enforced by the database
    trigger installed in revision ``f6a7b8c9d0e1``.
    """

    __tablename__ = "technician_profiles"
    __table_args__ = (
        CheckConstraint(
            r"phone_number IS NULL OR phone_number ~ '^\+[1-9][0-9]{6,14}$'",
            name="ck_technician_profiles_phone_number_e164",
        ).ddl_if(dialect="postgresql"),
        Index("ix_technician_profiles_email", "email", unique=True),
        Index("ix_technician_profiles_active_available", "is_active", "is_available"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    skills: Mapped[list[TechnicianSkill]] = relationship(
        back_populates="technician",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list[TicketAssignment]] = relationship(back_populates="technician")
