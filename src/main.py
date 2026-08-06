import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.openapi_responses import INTERNAL_SERVER_ERROR_RESPONSE
from src.api.router import api_router
from src.config import get_settings
from src.database.session import engine
from src.models.api.errors import INTERNAL_ERROR, DomainError
from src.models.api.health import HealthResponse, ReadinessResponse
from src.services.readiness_service import ReadinessService

logger = logging.getLogger(__name__)

settings = get_settings()

OPENAPI_DESCRIPTION = """
FixIt Agent API is the MVP backend for apartment maintenance reporting.

Residents use the API to view active unit memberships, request private attachment
upload targets, create maintenance tickets, list their accessible tickets, and
retrieve short-lived attachment download URLs.

BQL staff use the API to read the system-wide ticket list for the current MVP.

Authentication for protected endpoints uses Supabase Bearer access tokens:
`Authorization: Bearer <SUPABASE_ACCESS_TOKEN>`. In Swagger UI, use the
Authorize button and paste only an access token, for example
`eyJ...supabase-access-token`. Do not use Supabase secret or service-role keys.
"""


def openapi_tags() -> list[dict[str, str]]:
    tags = [
        {"name": "Health", "description": "Public liveness and readiness checks."},
        {"name": "Auth", "description": "Authenticated Resident or BQL actor context."},
        {"name": "Units", "description": "Resident unit membership APIs."},
        {"name": "Storage", "description": "Private Supabase Storage signed upload targets for ticket attachments."},
        {"name": "Tickets", "description": "Resident ticket creation, listing, detail, and attachment download APIs."},
        {"name": "BQL", "description": "BQL read APIs for the MVP ticket queue."},
    ]
    if settings.enable_legacy_agent_routes and settings.app_env == "development":
        tags.append(
            {
                "name": "Agent Legacy",
                "description": "Development-only legacy starter Agent routes guarded by a feature flag.",
            }
        )
    return tags


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_runtime_safety()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
    print("Shutting down...")


app = FastAPI(
    title="FixIt Agent API",
    description=OPENAPI_DESCRIPTION,
    version="1.0.0",
    openapi_tags=openapi_tags(),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled request error",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
            "safe_message": "Internal server error.",
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": INTERNAL_ERROR,
                "message": "Internal server error.",
                "details": None,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.get(
    "/health",
    tags=["Health"],
    response_model=HealthResponse,
    summary="Check API liveness",
    description=(
        "Public unauthenticated liveness check. Returns the application name, current environment label, "
        "and a simple ok status without checking external dependencies."
    ),
    operation_id="health_check",
    responses={500: INTERNAL_SERVER_ERROR_RESPONSE},
)
async def health() -> HealthResponse:
    return {"application": settings.app_name, "environment": settings.app_env, "status": "ok"}


@app.get(
    "/ready",
    tags=["Health"],
    response_model=ReadinessResponse,
    summary="Check API readiness",
    description=(
        "Public unauthenticated readiness check. It safely reports database, migration, Supabase Auth, "
        "and Supabase Storage configuration statuses without exposing hostnames, URLs, credentials, "
        "stack traces, or internal exception messages."
    ),
    operation_id="readiness_check",
    responses={
        503: {
            "model": ReadinessResponse,
            "description": "A required dependency is missing, unavailable, or not ready.",
        },
        500: INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def ready() -> ReadinessResponse | JSONResponse:
    payload, status_code = ReadinessService(settings, engine).check()
    if status_code != 200:
        return JSONResponse(status_code=status_code, content=payload)
    return payload
