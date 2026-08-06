"""Resident business profile persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.resident_unit_membership import ResidentUnitMembership
    from src.database.models.ticket import Ticket
    from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession


class Resident(Base):
    """Resident profile linked to a Supabase Auth user ID."""

    __tablename__ = "residents"
    __table_args__ = (
        CheckConstraint(
            r"phone_number ~ '^\+[1-9][0-9]{6,14}$'",
            name="ck_residents_phone_number_e164",
        ).ddl_if(dialect="postgresql"),
        Index("ix_residents_phone_number", "phone_number", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tickets: Mapped[list[Ticket]] = relationship(back_populates="resident")
    unit_memberships: Mapped[list[ResidentUnitMembership]] = relationship(back_populates="resident")
    ticket_attachment_upload_sessions: Mapped[list[TicketAttachmentUploadSession]] = relationship(back_populates="resident")
