"""Assignment domain API schemas for Technician and BQL endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import AssignmentStatus, Category, Priority, TicketStatus


class TechnicianSummaryResponse(BaseModel):
    """Technician record returned in the BQL roster list."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID = Field(description="Technician UUID.")
    email: str = Field(description="Technician email address.")
    full_name: str | None = Field(description="Optional display name.")
    phone_number: str | None = Field(description="Optional E.164 phone number.")
    is_active: bool = Field(description="Whether the technician profile is active.")
    is_available: bool = Field(description="Whether the technician is available for new assignments.")
    skills: list[str] = Field(
        default_factory=list,
        description="Category values the technician is qualified to handle.",
    )


class TechnicianListResponse(BaseModel):
    """Paginated BQL roster of technicians."""

    model_config = ConfigDict(extra="forbid")

    items: list[TechnicianSummaryResponse] = Field(description="Technicians returned for the current page.")
    page: int = Field(description="Current page number (starts at 1).")
    page_size: int = Field(description="Page size used for this response.")
    total: int = Field(description="Total matching technicians.")


class AssignTicketRequest(BaseModel):
    """BQL request body to assign a ticket to a technician."""

    model_config = ConfigDict(extra="forbid")

    technician_id: UUID = Field(description="UUID of the technician to assign the ticket to.")
    assignment_note: str | None = Field(
        default=None,
        max_length=500,
        description="Optional internal note visible to BQL and the assigned technician.",
    )


class AssignmentAttachmentResponse(BaseModel):
    """Safe ticket-attachment metadata exposed through an actor-authorized endpoint."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Attachment metadata UUID.")
    mime_type: str | None = Field(description="Stored MIME type, when known.")
    file_size: int | None = Field(description="Stored object size in bytes, when known.")
    downloadable: bool = Field(default=True, description="Whether a signed download URL can be requested.")
    download_url_endpoint: str = Field(
        description="Actor-scoped endpoint that returns a short-lived signed URL; no private path is exposed."
    )


class AssignmentTicketSummary(BaseModel):
    """Minimal ticket information included in assignment responses."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    title: str
    description: str
    status: TicketStatus
    category: Category | None
    priority: Priority | None
    location_description: str | None
    attachments: list[AssignmentAttachmentResponse] = Field(default_factory=list)


class AssignmentResponse(BaseModel):
    """Assignment record returned to Technician or BQL endpoints."""

    model_config = ConfigDict(extra="forbid", from_attributes=False)

    id: UUID = Field(description="Assignment UUID.")
    ticket_id: UUID = Field(description="Ticket UUID.")
    technician_id: UUID = Field(description="Assigned technician UUID.")
    status: AssignmentStatus = Field(description="Current assignment status.")
    assignment_note: str | None = Field(description="Optional BQL note.")
    work_note: str | None = Field(description="Technician work note, when recorded.")
    unable_reason: str | None = Field(description="Reason the technician could not handle the work.")
    assigned_at: datetime = Field(description="When the assignment was created.")
    accepted_at: datetime | None = Field(description="When the technician accepted.")
    started_at: datetime | None = Field(description="When work-in-progress was set.")
    ended_at: datetime | None = Field(description="When the assignment ended (unable/complete).")
    is_active: bool = Field(description="Whether this is the current active assignment.")
    ticket: AssignmentTicketSummary = Field(description="Parent ticket summary.")


class AssignmentStatusUpdateRequest(BaseModel):
    """Technician request to transition assignment status."""

    model_config = ConfigDict(extra="forbid")

    status: AssignmentStatus = Field(
        description=(
            "Requested target status. Allowed: in_progress (from accepted), "
            "unable_to_handle (from assigned/accepted/in_progress)."
        )
    )
    work_note: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional work note about cause, materials, or actions taken.",
    )
    unable_reason: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Required non-blank reason when status is unable_to_handle.",
    )
