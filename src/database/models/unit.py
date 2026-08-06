"""Unit persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.resident_unit_membership import ResidentUnitMembership
    from src.database.models.ticket import Ticket


class Unit(Base):
    """Physical building unit associated with reported tickets."""

    __tablename__ = "units"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    building_code: Mapped[str] = mapped_column(String(50), nullable=False)
    floor: Mapped[str] = mapped_column(String(50), nullable=False)
    unit_number: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    tickets: Mapped[list[Ticket]] = relationship(back_populates="unit")
    resident_memberships: Mapped[list[ResidentUnitMembership]] = relationship(back_populates="unit")
