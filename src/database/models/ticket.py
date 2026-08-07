"""Ticket persistence model aligned with Self_Dev_Docs v2."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import ClassificationStatus, Priority, Severity, TicketStatus

if TYPE_CHECKING:
    from src.database.models.ai_analysis import AIAnalysisRun
    from src.database.models.attachment import TicketAttachment
    from src.database.models.category import CategoryCatalog
    from src.database.models.information_request import InformationRequest
    from src.database.models.location import Location
    from src.database.models.notification import Notification
    from src.database.models.ticket_status_history import TicketStatusHistory
    from src.database.models.unit import Unit
    from src.database.models.user_profile import UserProfile


def enum_values(enum_class):
    return [member.value for member in enum_class]


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reporter_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_profiles.user_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id: Mapped[UUID] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus, name="ticket_status_v2_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
        default=TicketStatus.NEW,
        server_default=TicketStatus.NEW.value,
    )
    classification_status: Mapped[ClassificationStatus] = mapped_column(
        SQLEnum(
            ClassificationStatus,
            name="classification_status_enum",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=ClassificationStatus.PENDING,
        server_default=ClassificationStatus.PENDING.value,
    )
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True)
    priority: Mapped[Priority | None] = mapped_column(
        SQLEnum(Priority, name="priority_level_enum", native_enum=True, values_callable=enum_values), nullable=True
    )
    severity: Mapped[Severity | None] = mapped_column(
        SQLEnum(Severity, name="severity_v2_enum", native_enum=True, values_callable=enum_values), nullable=True
    )
    red_flag_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    score_total: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    sla_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    reporter: Mapped[UserProfile] = relationship()
    source_unit: Mapped[Unit] = relationship(back_populates="tickets")
    location: Mapped[Location] = relationship(back_populates="tickets")
    category: Mapped[CategoryCatalog | None] = relationship(back_populates="tickets")
    attachments: Mapped[list[TicketAttachment]] = relationship(back_populates="ticket", cascade="all, delete-orphan")
    ai_analysis_runs: Mapped[list[AIAnalysisRun]] = relationship(back_populates="ticket", cascade="all, delete-orphan")
    status_history: Mapped[list[TicketStatusHistory]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    information_requests: Mapped[list[InformationRequest]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="ticket")
