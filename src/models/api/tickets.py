"""Ticket API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.enums import Category, Priority, Severity, TicketStatus

TICKET_CREATE_EXAMPLE = {
    "title": "Rò rỉ nước tại hành lang tầng 10",
    "description": "Nước đang chảy từ trần gần thang máy và làm sàn bị trơn.",
    "unit_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "location_description": "Hành lang tầng 10, trước thang máy số 2",
    "attachment_upload_ids": ["6ba7b810-9dad-11d1-80b4-00c04fd430c8"],
}

TICKET_ATTACHMENT_EXAMPLE = {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "mime_type": "image/jpeg",
    "file_size": 245760,
    "downloadable": True,
    "download_url_endpoint": (
        "/api/v1/tickets/8a7f6c5d-4b3a-4210-9c8d-123456789abc/"
        "attachments/7c9e6679-7425-40de-944b-e07fc1f90ae7/download-url"
    ),
}

TICKET_RESPONSE_EXAMPLE = {
    "id": "8a7f6c5d-4b3a-4210-9c8d-123456789abc",
    "title": "Rò rỉ nước tại hành lang tầng 10",
    "description": "Nước đang chảy từ trần gần thang máy và làm sàn bị trơn.",
    "status": "new",
    "category": None,
    "severity": None,
    "priority": None,
    "location_description": "Hành lang tầng 10, trước thang máy số 2",
    "created_at": "2026-08-05T09:15:00Z",
    "updated_at": "2026-08-05T09:15:00Z",
    "resolved_at": None,
    "estimated_resolution_at": None,
    "estimated_resolution_text": "Đang phân tích",
    "attachments": [TICKET_ATTACHMENT_EXAMPLE],
}

TICKET_LIST_EXAMPLE = {
    "items": [{**TICKET_RESPONSE_EXAMPLE, "attachments": []}],
    "page": 1,
    "page_size": 20,
    "total": 1,
}


class TicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": TICKET_CREATE_EXAMPLE})

    title: str = Field(
        min_length=3,
        max_length=255,
        description="Short resident-facing ticket title.",
        examples=["Rò rỉ nước tại hành lang tầng 10"],
    )
    description: str = Field(
        min_length=10,
        max_length=5000,
        description="Detailed resident description of the issue.",
        examples=["Nước đang chảy từ trần gần thang máy và làm sàn bị trơn."],
    )
    unit_id: UUID | None = Field(
        default=None,
        description="Resident unit UUID. Required only when the resident has more than one active unit membership.",
    )
    location_description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional location detail within or near the unit.",
        examples=["Hành lang tầng 10, trước thang máy số 2"],
    )
    attachment_upload_ids: list[UUID] = Field(
        default_factory=list,
        max_length=5,
        description=(
            "Upload session UUIDs returned by the signed upload endpoint. Sessions are verified and consumed "
            "transactionally during ticket creation."
        ),
    )

    @field_validator("attachment_upload_ids")
    @classmethod
    def no_duplicate_upload_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate attachment upload IDs are not allowed.")
        return value


class TicketAttachmentResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        json_schema_extra={"example": TICKET_ATTACHMENT_EXAMPLE},
    )

    id: UUID = Field(description="Attachment metadata UUID.")
    mime_type: str | None = Field(description="Stored attachment MIME type, when known.")
    file_size: int | None = Field(description="Stored attachment size in bytes, when known.")
    downloadable: bool = Field(default=True, description="Whether the attachment can be downloaded through this API.")
    download_url_endpoint: str = Field(
        description="API endpoint that returns a short-lived signed download URL. Private object paths are not exposed."
    )


class AttachmentDownloadUrlResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "attachment_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "signed_download_url": "https://storage.example.invalid/object/sign/fictional",
                "expires_in": 300,
                "mime_type": "image/jpeg",
                "file_size": 245760,
            }
        },
    )

    attachment_id: UUID = Field(description="Attachment metadata UUID.")
    signed_download_url: str = Field(description="Short-lived signed URL for direct Supabase Storage download.")
    expires_in: int = Field(description="Signed download URL lifetime in seconds.", examples=[300])
    mime_type: str | None = Field(description="Stored attachment MIME type, when known.")
    file_size: int | None = Field(description="Stored attachment size in bytes, when known.")


class TicketResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": TICKET_RESPONSE_EXAMPLE})

    id: UUID = Field(description="Ticket UUID.")
    title: str = Field(description="Resident-facing ticket title.")
    description: str = Field(description="Resident-provided ticket description.")
    status: TicketStatus = Field(description="Current ticket lifecycle status.")
    category: Category | None = Field(description="AI-assigned category when analysis has populated it; otherwise null.")
    severity: Severity | None = Field(description="AI-assigned severity when analysis has populated it; otherwise null.")
    priority: Priority | None = Field(description="Scored priority when analysis has populated it; otherwise null.")
    location_description: str | None = Field(description="Optional resident-provided location details.")
    created_at: datetime = Field(description="Ticket creation timestamp.")
    updated_at: datetime = Field(description="Last ticket update timestamp.")
    resolved_at: datetime | None = Field(description="Resolution timestamp, or null while unresolved.")
    estimated_resolution_at: datetime | None = Field(
        default=None,
        description="Estimated resolution timestamp. Currently null until an approved SLA formula is implemented.",
    )
    estimated_resolution_text: str = Field(
        default="Đang phân tích",
        description="Human-readable estimated resolution placeholder while SLA estimation is deferred.",
    )
    attachments: list[TicketAttachmentResponse] = Field(
        default_factory=list,
        description="Attachment metadata and download endpoint references. Private Storage paths are not returned.",
    )


class TicketListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": TICKET_LIST_EXAMPLE})

    items: list[TicketResponse] = Field(description="Tickets returned for the current page.")
    page: int = Field(description="Current page number. Page numbering starts at 1.")
    page_size: int = Field(description="Requested page size, between 1 and 100.")
    total: int = Field(description="Total number of tickets matching the filters.")
