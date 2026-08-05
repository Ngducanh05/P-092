"""AI analysis run persistence model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import Category, Severity

if TYPE_CHECKING:
    from src.database.models.scoring_result import TicketScoringResult
    from src.database.models.ticket import Ticket


def enum_values(enum_class: type[Category] | type[Severity]) -> list[str]:
    """Return stable persisted values for string enums."""
    return [member.value for member in enum_class]


class AIAnalysisRun(Base):
    """Historical AI analysis result for a ticket.

    model_name is nullable so tests and future non-LLM analysis paths can persist
    historical records even when a model identifier is unavailable.
    """

    __tablename__ = "ai_analysis_runs"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_ai_analysis_runs_confidence_range"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[Category] = mapped_column(
        SQLEnum(Category, name="category_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    severity: Mapped[Severity] = mapped_column(
        SQLEnum(Severity, name="severity_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    red_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    text_categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    image_category: Mapped[Category | None] = mapped_column(
        SQLEnum(Category, name="category_enum", native_enum=True, values_callable=enum_values),
        nullable=True,
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    recommended_department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ticket: Mapped[Ticket] = relationship(back_populates="ai_analysis_runs")
    scoring_results: Mapped[list[TicketScoringResult]] = relationship(back_populates="ai_analysis_run")
