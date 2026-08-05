"""Technician category skill persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import Category

if TYPE_CHECKING:
    from src.database.models.technician_profile import TechnicianProfile


def enum_values(enum_class: type[Category]) -> list[str]:
    """Return stable persisted values for string enums."""
    return [member.value for member in enum_class]


class TechnicianSkill(Base):
    """Category capability declared for a technician."""

    __tablename__ = "technician_skills"
    __table_args__ = (
        UniqueConstraint("technician_id", "category", name="uq_technician_skills_technician_category"),
        Index("ix_technician_skills_category", "category"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    technician_id: Mapped[UUID] = mapped_column(
        ForeignKey("technician_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    category: Mapped[Category] = mapped_column(
        SQLEnum(Category, name="category_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    technician: Mapped[TechnicianProfile] = relationship(back_populates="skills")
