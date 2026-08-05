"""Coordinator routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_coordinator
from src.api.routes.tickets import bounded_page_size, ticket_response
from src.database.models.user import User
from src.models.api.tickets import TicketListResponse
from src.models.enums import Category, Priority, TicketStatus
from src.services.ticket_service import TicketService

router = APIRouter()


@router.get("/tickets", response_model=TicketListResponse)
def coordinator_tickets(
    _user: User = Depends(require_coordinator),
    db: Session = Depends(get_db),
    category: Category | None = None,
    priority: Priority | None = None,
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Depends(bounded_page_size),
) -> TicketListResponse:
    items, total = TicketService(db).list_coordinator_tickets(
        page, page_size, status_filter, category, priority, created_from, created_to
    )
    return TicketListResponse(items=[ticket_response(item) for item in items], page=page, page_size=page_size, total=total)
