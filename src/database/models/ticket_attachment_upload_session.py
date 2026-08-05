"""Ticket attachment upload-session persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.user import User


class TicketAttachmentUploadSession(Base):
    """Trusted backend state for a single private attachment upload."""

    __tablename__ = "ticket_attachment_upload_sessions"
    __table_args__ = (
        CheckConstraint("file_size > 0", name="ck_ticket_attachment_upload_sessions_file_size_positive"),
        CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_ticket_attachment_upload_sessions_mime_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'consumed', 'expired')",
            name="ck_ticket_attachment_upload_sessions_status",
        ),
        CheckConstraint(
            "length(storage_path) > 0 AND length(storage_path) <= 1024",
            name="ck_ticket_attachment_upload_sessions_storage_path_length",
        ),
        CheckConstraint("expires_at > created_at", name="ck_ticket_attachment_upload_sessions_expiry_order"),
        UniqueConstraint("storage_path", name="uq_ticket_attachment_upload_sessions_storage_path"),
        Index("ix_ticket_attachment_upload_sessions_owner_status", "owner_user_id", "status"),
        Index("ix_ticket_attachment_upload_sessions_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    object_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped[User] = relationship(back_populates="ticket_attachment_upload_sessions")
