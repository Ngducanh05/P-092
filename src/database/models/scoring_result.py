"""Ticket scoring result persistence model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import Priority

if TYPE_CHECKING:
    from src.database.models.ai_analysis import AIAnalysisRun
    from src.database.models.ticket import Ticket


def enum_values(enum_class: type[Priority]) -> list[str]:
    """Return stable persisted values for string enums."""
    return [member.value for member in enum_class]


class TicketScoringResult(Base):
    """Historical priority scoring result for a ticket."""

    __tablename__ = "ticket_scoring_results"
    __table_args__ = (
        CheckConstraint("severity_score >= 0 AND severity_score <= 40", name="ck_ticket_scoring_severity_range"),
        CheckConstraint("red_flag_score >= 0 AND red_flag_score <= 30", name="ck_ticket_scoring_red_flag_range"),
        CheckConstraint("impact_score >= 0 AND impact_score <= 15", name="ck_ticket_scoring_impact_range"),
        CheckConstraint("density_score >= 0 AND density_score <= 10", name="ck_ticket_scoring_density_range"),
        CheckConstraint("age_score >= 0 AND age_score <= 5", name="ck_ticket_scoring_age_range"),
        CheckConstraint("total_score >= 0 AND total_score <= 100", name="ck_ticket_scoring_total_range"),
        CheckConstraint(
            "total_score = severity_score + red_flag_score + impact_score + density_score + age_score",
            name="ck_ticket_scoring_total_equals_components",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    ai_analysis_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    severity_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    red_flag_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    impact_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    density_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    age_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    priority: Mapped[Priority] = mapped_column(
        SQLEnum(Priority, name="priority_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    scoring_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ticket: Mapped[Ticket] = relationship(back_populates="scoring_results")
    ai_analysis_run: Mapped[AIAnalysisRun | None] = relationship(back_populates="scoring_results")
