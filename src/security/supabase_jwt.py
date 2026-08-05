"""Supabase access-token verification helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import jwt
from jwt import PyJWKClient
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from src.config import Settings
from src.models.api.errors import AUTH_TOKEN_EXPIRED, AUTH_TOKEN_INVALID, DomainError

ALLOWED_ALGORITHMS = ("RS256", "ES256")


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    auth_user_id: UUID
    email: str | None
    phone: str | None
    issuer: str
    audience: str | list[str]
    expires_at: datetime


class SupabaseJWTVerifier:
    """Verifies Supabase JWTs without trusting editable metadata."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks_client: PyJWKClient | None = None

    @property
    def issuer(self) -> str:
        return f"{self.settings.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"

    def refresh_jwks(self) -> None:
        self._jwks_client = None

    def verify(self, token: str) -> AuthenticatedPrincipal:
        mode = self.settings.supabase_jwt_verification_mode
        if mode == "jwks":
            return self._verify_jwks(token)
        if mode == "auth_server":
            return self._verify_auth_server(token)
        try:
            return self._verify_jwks(token)
        except DomainError as exc:
            if exc.details != "NO_COMPATIBLE_JWKS":
                raise
            return self._verify_auth_server(token)

    def _verify_jwks(self, token: str) -> AuthenticatedPrincipal:
        if not self.settings.supabase_url:
            raise DomainError(AUTH_TOKEN_INVALID, "JWT verification is not configured.", 401, "NO_COMPATIBLE_JWKS")
        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise DomainError(AUTH_TOKEN_INVALID, "Invalid access token.", 401) from exc
        algorithm = header.get("alg")
        if algorithm not in ALLOWED_ALGORITHMS:
            raise DomainError(AUTH_TOKEN_INVALID, "Unsupported token algorithm.", 401)
        if not header.get("kid"):
            raise DomainError(AUTH_TOKEN_INVALID, "Missing token key identifier.", 401)

        try:
            if self._jwks_client is None:
                self._jwks_client = PyJWKClient(self.jwks_url, cache_keys=True)
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[algorithm],
                audience=self.settings.supabase_jwt_audience,
                issuer=self.issuer,
                options={"require": ["exp", "sub"]},
            )
        except ExpiredSignatureError as exc:
            raise DomainError(AUTH_TOKEN_EXPIRED, "Access token has expired.", 401) from exc
        except Exception as exc:
            message = str(exc).lower()
            if "unable to find a signing key" in message or "jwks" in message:
                raise DomainError(AUTH_TOKEN_INVALID, "No compatible JWKS is available.", 401, "NO_COMPATIBLE_JWKS") from exc
            raise DomainError(AUTH_TOKEN_INVALID, "Invalid access token.", 401) from exc
        return self._principal_from_payload(payload)

    def _verify_auth_server(self, token: str) -> AuthenticatedPrincipal:
        if not self.settings.supabase_url or not self.settings.supabase_publishable_key:
            raise DomainError(AUTH_TOKEN_INVALID, "Auth server verification is not configured.", 401)
        try:
            response = httpx.get(
                f"{self.settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={"apikey": self.settings.supabase_publishable_key, "Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise DomainError(AUTH_TOKEN_INVALID, "Unable to verify access token.", 401) from exc
        if response.status_code == 401:
            raise DomainError(AUTH_TOKEN_INVALID, "Invalid access token.", 401)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        payload = {
            "sub": data.get("id"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "iss": self.issuer,
            "aud": self.settings.supabase_jwt_audience,
            "exp": int(datetime.now(UTC).timestamp()) + 300,
        }
        return self._principal_from_payload(payload)

    def _principal_from_payload(self, payload: dict[str, Any]) -> AuthenticatedPrincipal:
        subject = payload.get("sub")
        try:
            auth_user_id = UUID(str(subject))
        except (TypeError, ValueError) as exc:
            raise DomainError(AUTH_TOKEN_INVALID, "Invalid token subject.", 401) from exc
        if not payload.get("email") and not payload.get("phone"):
            raise DomainError(AUTH_TOKEN_INVALID, "Token must contain validated email or phone.", 401)
        return AuthenticatedPrincipal(
            auth_user_id=auth_user_id,
            email=payload.get("email"),
            phone=payload.get("phone"),
            issuer=str(payload.get("iss", "")),
            audience=payload.get("aud", ""),
            expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=UTC),
        )
