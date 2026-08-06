"""Notification persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.ticket import Ticket


class Notification(Base):
    """Stored notification for a Resident or BQL auth identity."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_auth_unread_created_at", "recipient_auth_user_id", "is_read", "created_at"),
        Index("ix_notifications_ticket_id", "ticket_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    recipient_auth_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ticket_id: Mapped[UUID | None] = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ticket: Mapped[Ticket | None] = relationship(back_populates="notifications")
