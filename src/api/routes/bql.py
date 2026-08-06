"""BQL routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_bql
from src.api.openapi_responses import AUTHENTICATED_RESPONSES
from src.api.routes.tickets import bounded_page_size, ticket_response
from src.database.models.bql_staff import BQLStaff
from src.models.api.tickets import TicketListResponse
from src.models.enums import Category, Priority, TicketStatus
from src.services.ticket_service import TicketService

router = APIRouter()


@router.get(
    "/tickets",
    response_model=TicketListResponse,
    summary="List BQL tickets",
    description=(
        "BQL-only endpoint. Returns the system-wide MVP ticket queue with optional status, category, priority, "
        "and ISO 8601 created_at range filters. Results are ordered by priority and creation time, then paginated."
    ),
    operation_id="list_bql_tickets",
    responses=AUTHENTICATED_RESPONSES,
)
def bql_tickets(
    _staff: BQLStaff = Depends(require_bql),
    db: Session = Depends(get_db),
    category: Category | None = Query(default=None, description="Filter by AI-assigned ticket category."),
    priority: Priority | None = Query(default=None, description="Filter by scored ticket priority."),
    status_filter: TicketStatus | None = Query(default=None, alias="status", description="Filter by ticket status."),
    created_from: datetime | None = Query(
        default=None,
        description="Filter tickets created at or after this ISO 8601 timestamp.",
    ),
    created_to: datetime | None = Query(
        default=None,
        description="Filter tickets created at or before this ISO 8601 timestamp.",
    ),
    page: int = Query(default=1, ge=1, description="Page number. Page numbering starts at 1."),
    page_size: int = Depends(bounded_page_size),
) -> TicketListResponse:
    items, total = TicketService(db).list_bql_tickets(
        page, page_size, status_filter, category, priority, created_from, created_to
    )
    return TicketListResponse(items=[ticket_response(item) for item in items], page=page, page_size=page_size, total=total)
