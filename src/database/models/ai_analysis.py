"""Versioned AI analysis run matching the Backend/Agent contract in Self_Dev_Docs v2."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import AnalysisRunStatus, Priority, Severity, SeveritySource

if TYPE_CHECKING:
    from src.database.models.ticket import Ticket

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


def enum_values(enum_class):
    return [member.value for member in enum_class]


class AIAnalysisRun(Base):
    __tablename__ = "ai_analysis_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    text_model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vision_model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("scoring_rule_versions.id", ondelete="SET NULL"), nullable=True
    )
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text_categories: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list, server_default="[]")
    image_categories: Mapped[list[str] | None] = mapped_column(JSON_TYPE, nullable=True)
    red_flag_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    red_flag_signal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    severity: Mapped[Severity | None] = mapped_column(
        SQLEnum(Severity, name="severity_v2_enum", native_enum=True, values_callable=enum_values), nullable=True
    )
    severity_source: Mapped[SeveritySource | None] = mapped_column(
        SQLEnum(SeveritySource, name="severity_source_enum", native_enum=True, values_callable=enum_values), nullable=True
    )
    category_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score_components: Mapped[dict[str, object] | None] = mapped_column(JSON_TYPE, nullable=True)
    score_total: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    priority_raw: Mapped[Priority | None] = mapped_column(
        SQLEnum(Priority, name="priority_level_enum", native_enum=True, values_callable=enum_values), nullable=True
    )
    priority_final: Mapped[Priority | None] = mapped_column(
        SQLEnum(Priority, name="priority_level_enum", native_enum=True, values_callable=enum_values), nullable=True
    )
    ceiling_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    status: Mapped[AnalysisRunStatus] = mapped_column(
        SQLEnum(AnalysisRunStatus, name="analysis_run_status_enum", native_enum=True, values_callable=enum_values),
        nullable=False,
        default=AnalysisRunStatus.RUNNING,
        server_default=AnalysisRunStatus.RUNNING.value,
    )
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ticket: Mapped[Ticket] = relationship(back_populates="ai_analysis_runs")
