"""Ticket API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.enums import Category, Priority, Severity, TicketStatus


class TicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10, max_length=5000)
    unit_id: UUID | None = None
    location_description: str | None = Field(default=None, max_length=500)
    attachment_upload_ids: list[UUID] = Field(default_factory=list, max_length=5)

    @field_validator("attachment_upload_ids")
    @classmethod
    def no_duplicate_upload_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate attachment upload IDs are not allowed.")
        return value


class TicketAttachmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    mime_type: str | None
    file_size: int | None
    downloadable: bool = True
    download_url_endpoint: str


class AttachmentDownloadUrlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attachment_id: UUID
    signed_download_url: str
    expires_in: int
    mime_type: str | None
    file_size: int | None


class TicketResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str
    description: str
    status: TicketStatus
    category: Category | None
    severity: Severity | None
    priority: Priority | None
    location_description: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    estimated_resolution_at: datetime | None = None
    estimated_resolution_text: str = "Đang phân tích"
    attachments: list[TicketAttachmentResponse] = Field(default_factory=list)


class TicketListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TicketResponse]
    page: int
    page_size: int
    total: int
