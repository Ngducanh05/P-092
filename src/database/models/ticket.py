"""Ticket persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import Category, Priority, Severity, TicketStatus

if TYPE_CHECKING:
    from src.database.models.ai_analysis import AIAnalysisRun
    from src.database.models.attachment import TicketAttachment
    from src.database.models.notification import Notification
    from src.database.models.resident import Resident
    from src.database.models.scoring_result import TicketScoringResult
    from src.database.models.ticket_assignment import TicketAssignment
    from src.database.models.ticket_status_history import TicketStatusHistory
    from src.database.models.unit import Unit


def enum_values(enum_class: type[Category] | type[Priority] | type[Severity] | type[TicketStatus]) -> list[str]:
    """Return stable persisted values for string enums."""
    return [member.value for member in enum_class]


class Ticket(Base):
    """Maintenance ticket reported by a resident."""

    __tablename__ = "tickets"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    resident_id: Mapped[UUID] = mapped_column(ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False, index=True)
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus, name="ticket_status_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
        default=TicketStatus.NEW,
        server_default=TicketStatus.NEW.value,
    )
    category: Mapped[Category | None] = mapped_column(
        SQLEnum(Category, name="category_enum", native_enum=True, values_callable=enum_values),
        nullable=True,
    )
    severity: Mapped[Severity | None] = mapped_column(
        SQLEnum(Severity, name="severity_enum", native_enum=True, values_callable=enum_values),
        nullable=True,
    )
    priority: Mapped[Priority | None] = mapped_column(
        SQLEnum(Priority, name="priority_enum", native_enum=True, values_callable=enum_values),
        nullable=True,
    )
    location_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    resident: Mapped[Resident] = relationship(back_populates="tickets")
    unit: Mapped[Unit] = relationship(back_populates="tickets")
    attachments: Mapped[list[TicketAttachment]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    ai_analysis_runs: Mapped[list[AIAnalysisRun]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    scoring_results: Mapped[list[TicketScoringResult]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    status_history: Mapped[list[TicketStatusHistory]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list[TicketAssignment]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="ticket")
