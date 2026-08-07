"""Resident-facing ticket contracts aligned with Self_Dev_Docs v2."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.enums import ClassificationStatus, TicketStatus


class TicketCreateRequest(BaseModel):
    """Secure signed-upload variant of POST /tickets.

    Self Dev specifies text and/or image plus a canonical location. This project
    keeps the existing one-time signed-upload session instead of accepting raw
    private object paths from the client.
    """

    model_config = ConfigDict(extra="forbid")

    location_id: UUID
    description: str | None = Field(default=None, max_length=5000)
    attachment_upload_ids: list[UUID] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def text_or_image_required(self):
        text_ok = bool(self.description and self.description.strip())
        if not text_ok and not self.attachment_upload_ids:
            raise ValueError("At least description or one image upload is required.")
        if len(self.attachment_upload_ids) != len(set(self.attachment_upload_ids)):
            raise ValueError("Duplicate attachment upload IDs are not allowed.")
        return self


class TicketCreatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: UUID
    status: TicketStatus
    classification_status: ClassificationStatus
    display_status: str


class TicketAttachmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    mime_type: str | None
    size_bytes: int | None
    download_url_endpoint: str


class TicketTimelineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_status: TicketStatus | None
    to_status: TicketStatus
    reason: str | None
    created_at: datetime


class ResidentTimelineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_status: str
    reason: str | None
    created_at: datetime


class ResidentTicketResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    description: str | None
    display_status: str
    category_display_name: str | None
    priority_description: str | None
    estimated_resolution_text: str
    created_at: datetime
    updated_at: datetime
    available_actions: list[str]
    attachments: list[TicketAttachmentResponse] = Field(default_factory=list)
    timeline: list[ResidentTimelineItem] = Field(default_factory=list)


class TicketListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ResidentTicketResponse]
    page: int
    page_size: int
    total: int


class AttachmentDownloadUrlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attachment_id: UUID
    signed_download_url: str
    expires_in: int
    mime_type: str | None
    size_bytes: int | None


class TicketSupplementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    information_request_id: UUID
    description: str | None = Field(default=None, max_length=5000)
    attachment_upload_ids: list[UUID] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def payload_required(self):
        if not (self.description and self.description.strip()) and not self.attachment_upload_ids:
            raise ValueError("Supplement must include description or image.")
        return self
