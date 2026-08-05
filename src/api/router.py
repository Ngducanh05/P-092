"""Central API router."""

from fastapi import APIRouter

from src.api.routes import auth, coordinator, legacy, storage, tickets, units

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(units.router, prefix="/units", tags=["Units"])
api_router.include_router(storage.router, prefix="/storage", tags=["Storage"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
api_router.include_router(coordinator.router, prefix="/coordinator", tags=["Coordinator"])
api_router.include_router(legacy.router, tags=["Agent Legacy"])
