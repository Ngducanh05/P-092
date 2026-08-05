"""Ticket status transition history persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import TicketStatus

if TYPE_CHECKING:
    from src.database.models.ticket import Ticket
    from src.database.models.user import User


def enum_values(enum_class: type[TicketStatus]) -> list[str]:
    """Return stable persisted values for string enums."""
    return [member.value for member in enum_class]


class TicketStatusHistory(Base):
    """Append-only record of a ticket status transition."""

    __tablename__ = "ticket_status_history"
    __table_args__ = (Index("ix_ticket_status_history_ticket_created_at", "ticket_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    from_status: Mapped[TicketStatus | None] = mapped_column(
        SQLEnum(TicketStatus, name="ticket_status_enum", native_enum=True, values_callable=enum_values),
        nullable=True,
    )
    to_status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus, name="ticket_status_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    changed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ticket: Mapped[Ticket] = relationship(back_populates="status_history")
    changed_by_user: Mapped[User | None] = relationship(
        back_populates="status_changes",
        foreign_keys=[changed_by_user_id],
    )
