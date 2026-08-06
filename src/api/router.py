"""Central API router."""

from fastapi import APIRouter

from src.api.routes import auth, bql, storage, tickets, units
from src.config import get_settings

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(units.router, prefix="/units", tags=["Units"])
api_router.include_router(storage.router, prefix="/storage", tags=["Storage"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
api_router.include_router(bql.router, prefix="/bql", tags=["BQL"])

settings = get_settings()
if settings.enable_legacy_agent_routes and settings.app_env == "development":
    from src.api.routes import legacy

    api_router.include_router(legacy.router, tags=["Agent Legacy"])
