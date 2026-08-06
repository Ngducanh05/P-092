"""Resident-to-unit membership persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.resident import Resident
    from src.database.models.unit import Unit


class ResidentUnitMembership(Base):
    """Link between a resident profile and a physical unit."""

    __tablename__ = "resident_unit_memberships"
    __table_args__ = (
        UniqueConstraint("resident_id", "unit_id", name="uq_resident_unit_memberships_resident_unit"),
        Index("ix_resident_unit_memberships_resident_active", "resident_id", "is_active"),
        Index("ix_resident_unit_memberships_unit_active", "unit_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    resident_id: Mapped[UUID] = mapped_column(ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False)
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id", ondelete="RESTRICT"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    resident: Mapped[Resident] = relationship(back_populates="unit_memberships")
    unit: Mapped[Unit] = relationship(back_populates="resident_memberships")
