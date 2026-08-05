"""User persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, func, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import Role

if TYPE_CHECKING:
    from src.database.models.audit_log import AuditLog
    from src.database.models.notification import Notification
    from src.database.models.technician_profile import TechnicianProfile
    from src.database.models.ticket import Ticket
    from src.database.models.ticket_assignment import TicketAssignment
    from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession
    from src.database.models.ticket_status_history import TicketStatusHistory
    from src.database.models.user_unit_membership import UserUnitMembership


def enum_values(enum_class: type[Role]) -> list[str]:
    """Return stable persisted values for string enums."""
    return [member.value for member in enum_class]


class User(Base):
    """Application user that can own maintenance tickets."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone_number IS NOT NULL", name="ck_users_email_or_phone"),
        CheckConstraint(
            r"phone_number IS NULL OR phone_number ~ '^\+[1-9][0-9]{6,14}$'",
            name="ck_users_phone_number_e164",
        ).ddl_if(dialect="postgresql"),
        Index("ix_users_email_not_null", "email", unique=True, postgresql_where=text("email IS NOT NULL")),
        Index(
            "ix_users_phone_number_not_null",
            "phone_number",
            unique=True,
            postgresql_where=text("phone_number IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[Role] = mapped_column(
        SQLEnum(Role, name="role_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tickets: Mapped[list[Ticket]] = relationship(back_populates="resident")
    unit_memberships: Mapped[list[UserUnitMembership]] = relationship(back_populates="user")
    technician_profile: Mapped[TechnicianProfile | None] = relationship(
        back_populates="user",
        uselist=False,
    )
    assigned_ticket_records: Mapped[list[TicketAssignment]] = relationship(
        back_populates="technician",
        foreign_keys="TicketAssignment.technician_id",
        primaryjoin="User.id == foreign(TicketAssignment.technician_id)",
        viewonly=True,
    )
    coordinator_assignment_records: Mapped[list[TicketAssignment]] = relationship(
        back_populates="assigned_by_user",
        foreign_keys="TicketAssignment.assigned_by_user_id",
    )
    status_changes: Mapped[list[TicketStatusHistory]] = relationship(
        back_populates="changed_by_user",
        foreign_keys="TicketStatusHistory.changed_by_user_id",
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="recipient_user")
    audit_logs: Mapped[list[AuditLog]] = relationship(
        back_populates="actor_user",
        foreign_keys="AuditLog.actor_user_id",
    )
    ticket_attachment_upload_sessions: Mapped[list[TicketAttachmentUploadSession]] = relationship(back_populates="owner")
