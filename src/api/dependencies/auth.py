"""Authentication and actor-resolution dependencies."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.config import get_settings
from src.database.models.bql_staff import BQLStaff
from src.database.models.resident import Resident
from src.models.api.errors import (
    ACTOR_FORBIDDEN,
    AUTH_PROFILE_CONFLICT,
    AUTH_PROFILE_INVALID,
    AUTH_TOKEN_INVALID,
    AUTH_TOKEN_MISSING,
    USER_INACTIVE,
    DomainError,
)
from src.repositories.profile_repository import ProfileRepository
from src.security.supabase_jwt import AuthenticatedPrincipal, SupabaseJWTVerifier
from src.services.phone import normalize_e164_phone

supabase_bearer = HTTPBearer(
    scheme_name="SupabaseBearerAuth",
    bearerFormat="JWT",
    description=(
        "Supabase access token. Send requests with "
        "`Authorization: Bearer <SUPABASE_ACCESS_TOKEN>`. Placeholder: `eyJ...supabase-access-token`."
    ),
    auto_error=False,
)


@dataclass(frozen=True)
class CurrentActor:
    actor_type: Literal["resident", "bql"]
    profile: Resident | BQLStaff
    principal: AuthenticatedPrincipal


@lru_cache
def get_supabase_jwt_verifier() -> SupabaseJWTVerifier:
    return SupabaseJWTVerifier(get_settings())


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(supabase_bearer),
    authorization: str | None = Header(default=None, include_in_schema=False),
    verifier: SupabaseJWTVerifier = Depends(get_supabase_jwt_verifier),
) -> AuthenticatedPrincipal:
    if credentials is None:
        if authorization:
            raise DomainError(AUTH_TOKEN_INVALID, "Invalid authorization header.", 401)
        raise DomainError(AUTH_TOKEN_MISSING, "Missing bearer token.", 401)
    if credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise DomainError(AUTH_TOKEN_INVALID, "Invalid authorization header.", 401)
    return verifier.verify(credentials.credentials)


def get_current_actor(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> CurrentActor:
    repo = ProfileRepository(db)
    resident = repo.get_resident(principal.auth_user_id)
    bql_staff = repo.get_bql_staff(principal.auth_user_id)
    phone = normalize_e164_phone(principal.phone)

    if resident is not None and bql_staff is not None:
        raise DomainError(AUTH_PROFILE_CONFLICT, "Authenticated identity has conflicting actor profiles.", 401)

    if resident is not None:
        if not phone or resident.phone_number != phone:
            raise DomainError(AUTH_PROFILE_INVALID, "Authenticated phone conflicts with resident profile.", 401)
        if not resident.is_active:
            raise DomainError(USER_INACTIVE, "Resident profile is inactive.", 403)
        return CurrentActor("resident", resident, principal)

    if bql_staff is not None:
        email = principal.email.casefold() if principal.email else None
        if not email or bql_staff.email.casefold() != email:
            raise DomainError(AUTH_PROFILE_INVALID, "Authenticated email conflicts with BQL profile.", 401)
        if not bql_staff.is_active:
            raise DomainError(USER_INACTIVE, "BQL profile is inactive.", 403)
        return CurrentActor("bql", bql_staff, principal)

    if not phone:
        raise DomainError(AUTH_PROFILE_INVALID, "Authenticated identity does not have a valid resident phone.", 401)
    try:
        resident = repo.create_resident_profile(principal.auth_user_id, phone)
    except IntegrityError as exc:
        raise DomainError(AUTH_PROFILE_INVALID, "Authenticated profile conflicts with an existing profile.", 401) from exc
    db.commit()
    db.refresh(resident)
    return CurrentActor("resident", resident, principal)


def require_resident(actor: CurrentActor = Depends(get_current_actor)) -> Resident:
    if actor.actor_type != "resident":
        raise DomainError(ACTOR_FORBIDDEN, "Actor is not allowed for this operation.", 403)
    return actor.profile  # type: ignore[return-value]


def require_bql(actor: CurrentActor = Depends(get_current_actor)) -> BQLStaff:
    if actor.actor_type != "bql":
        raise DomainError(ACTOR_FORBIDDEN, "Actor is not allowed for this operation.", 403)
    return actor.profile  # type: ignore[return-value]
