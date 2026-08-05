"""Supabase JWT verifier tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from src.config import Settings
from src.models.api.errors import AUTH_TOKEN_INVALID, DomainError
from src.security.supabase_jwt import SupabaseJWTVerifier


def _private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_rejects_alg_none_token():
    settings = Settings(
        app_env="test",
        supabase_url="https://example.supabase.co",
        supabase_jwt_audience="authenticated",
        supabase_jwt_verification_mode="jwks",
    )
    token = jwt.encode({"sub": str(uuid4()), "exp": datetime.now(UTC) + timedelta(minutes=5)}, key="", algorithm="none")

    with pytest.raises(DomainError) as exc:
        SupabaseJWTVerifier(settings).verify(token)

    assert exc.value.code == AUTH_TOKEN_INVALID


def test_principal_requires_uuid_subject():
    settings = Settings(app_env="test", supabase_url="https://example.supabase.co")
    verifier = SupabaseJWTVerifier(settings)

    with pytest.raises(DomainError):
        verifier._principal_from_payload(
            {"sub": "not-a-uuid", "email": "resident@example.com", "iss": verifier.issuer, "aud": "authenticated", "exp": 1}
        )
