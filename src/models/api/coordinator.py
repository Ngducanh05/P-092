"""Coordinator-only API contracts from Self_Dev_Docs v2."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.api.tickets import TicketAttachmentResponse, TicketTimelineItem
from src.models.enums import (
    Category,
    ClassificationStatus,
    Priority,
    ResolutionSource,
    Severity,
    SeveritySource,
    TicketStatus,
)


class CoordinatorAnalysisSummary(BaseModel):
    """Latest AI-only fields needed by the Coordinator, especially for P0 review."""

    model_config = ConfigDict(extra="forbid")

    run_number: int
    text_categories: list[Category]
    image_categories: list[Category] | None
    red_flag_text: bool
    red_flag_signal: bool
    severity: Severity | None
    severity_source: SeveritySource | None
    text_model_version: str | None
    vision_model_version: str | None
    error_code: str | None

class CoordinatorTicketResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    reporter_user_id: UUID
    source_unit_id: UUID
    location_id: UUID
    location_label: str | None
    description: str | None
    status: TicketStatus
    classification_status: ClassificationStatus
    display_code: str | None = None
    category_id: UUID | None
    category: Category | None
    priority: Priority | None
    severity: Severity | None
    red_flag_detected: bool
    score_total: float | None
    sla_started_at: datetime | None
    sla_due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int
    available_actions: list[str]
    latest_analysis: CoordinatorAnalysisSummary | None = None
    attachments: list[TicketAttachmentResponse] = Field(default_factory=list)
    timeline: list[TicketTimelineItem] = Field(default_factory=list)


class CoordinatorTicketListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CoordinatorTicketResponse]
    page: int
    page_size: int
    total: int


class ManualReviewResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: UUID
    resolution_source: ResolutionSource
    reason: str = Field(min_length=3, max_length=1000)


class RequestInformationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=3, max_length=2000)


class ClassificationOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: UUID | None = None
    priority: Priority | None = None
    reason: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def at_least_one_change(self):
        if self.category_id is None and self.priority is None:
            raise ValueError("category_id or priority is required.")
        return self


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    actor_user_id: UUID | None
    actor_role: str
    action: str
    entity_type: str
    entity_id: UUID
    before_data: dict[str, object] | None
    after_data: dict[str, object] | None
    reason: str | None
    request_id: UUID | None
    created_at: datetime


class TicketSummaryReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_category: dict[str, int]


class SlaPerformanceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completed_total: int
    completed_on_time: int
    compliance_rate: float | None


class ExportReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: str = Field(default="tickets-summary", pattern="^(tickets-summary|sla-performance)$")
    format: str = Field(default="CSV", pattern="^(CSV|csv)$")
