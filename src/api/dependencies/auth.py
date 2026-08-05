"""Authentication dependencies."""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.config import get_settings
from src.database.models.user import User
from src.models.api.errors import (
    AUTH_PROFILE_INVALID,
    AUTH_TOKEN_INVALID,
    AUTH_TOKEN_MISSING,
    USER_INACTIVE,
    DomainError,
)
from src.repositories.user_repository import UserRepository
from src.security.supabase_jwt import AuthenticatedPrincipal, SupabaseJWTVerifier


def get_current_principal(authorization: str | None = Header(default=None)) -> AuthenticatedPrincipal:
    if not authorization:
        raise DomainError(AUTH_TOKEN_MISSING, "Missing bearer token.", 401)
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise DomainError(AUTH_TOKEN_INVALID, "Invalid authorization header.", 401)
    return SupabaseJWTVerifier(get_settings()).verify(token)


def get_current_user(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> User:
    repo = UserRepository(db)
    user = repo.get_by_id(principal.auth_user_id)
    if user is None:
        if not principal.email and not principal.phone:
            raise DomainError(AUTH_PROFILE_INVALID, "Cannot create profile without email or phone.", 401)
        user = repo.create_resident_profile(principal.auth_user_id, principal.email, principal.phone)
        db.commit()
        db.refresh(user)
    if user.email and principal.email and user.email != principal.email:
        raise DomainError(AUTH_PROFILE_INVALID, "Authenticated email conflicts with application profile.", 401)
    if user.phone_number and principal.phone and user.phone_number != principal.phone:
        raise DomainError(AUTH_PROFILE_INVALID, "Authenticated phone conflicts with application profile.", 401)
    if not user.is_active:
        raise DomainError(USER_INACTIVE, "User is inactive.", 403)
    return user
