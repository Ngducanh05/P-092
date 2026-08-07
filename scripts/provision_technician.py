"""Backend-only helper for trusted Technician profile provisioning.

This script requires an existing Supabase Auth UUID. It never creates an Auth
identity and never accepts or stores a password.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import create_engine, text

from src.config import Settings, get_settings
from src.security.supabase_admin import build_supabase_admin_headers


@dataclass(frozen=True)
class SupabaseAuthUser:
    """Minimum trusted Auth user fields required for Technician provisioning."""

    id: UUID
    email: str


def parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(
        description=(
            "Provision or deactivate a FixIt Technician profile. "
            "Requires an existing Supabase Auth UUID — it never creates an Auth user."
        )
    )
    arg_parser.add_argument("action", choices=["provision", "deactivate"])
    arg_parser.add_argument("--auth-user-id", required=True, help="Existing Supabase Auth user UUID.")
    arg_parser.add_argument("--email", required=True, help="Expected email (must match Auth record).")
    arg_parser.add_argument("--full-name", default=None, help="Optional display name.")
    arg_parser.add_argument("--phone-number", default=None, help="Optional E.164 phone number.")
    arg_parser.add_argument("--dry-run", action="store_true")
    return arg_parser


def main() -> int:
    args = parser().parse_args()
    auth_user_id = _parse_uuid(args.auth_user_id)
    email = _normalize_email(args.email)
    phone_number = _normalize_optional_phone(args.phone_number)

    if args.dry_run:
        verb = "deactivate" if args.action == "deactivate" else "verify and provision"
        print(f"DRY RUN: would {verb} Technician profile {auth_user_id}.")
        return 0

    auth_user = fetch_auth_user(auth_user_id)
    if auth_user.email != email:
        raise SystemExit(
            "Supabase Auth email does not match the requested Technician profile email."
        )

    if args.action == "deactivate":
        deactivate_technician(auth_user_id, dry_run=False)
        return 0

    upsert_technician(
        auth_user_id=auth_user.id,
        email=auth_user.email,
        full_name=_clean_optional_text(args.full_name),
        phone_number=phone_number,
        dry_run=False,
    )
    return 0


def fetch_auth_user(auth_user_id: UUID) -> SupabaseAuthUser:
    """Read and validate an existing Supabase Auth identity."""
    settings = _require_supabase_admin_settings()
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{auth_user_id}",
                headers=build_supabase_admin_headers(settings.supabase_secret_key),
            )
    except httpx.RequestError as exc:
        raise SystemExit(
            "Unable to connect to Supabase Auth. Check SUPABASE_URL and the network."
        ) from exc

    if response.status_code == 404:
        raise SystemExit("Supabase Auth user was not found.")
    if response.status_code >= 400:
        raise SystemExit(f"Unable to inspect Supabase Auth user. HTTP {response.status_code}.")

    return _validated_auth_user_payload(response.json(), expected_id=auth_user_id)


def upsert_technician(
    auth_user_id: UUID,
    email: str,
    full_name: str | None,
    phone_number: str | None,
    dry_run: bool,
) -> None:
    """Create or reactivate the Technician profile using parameterized SQL."""
    if dry_run:
        print(f"DRY RUN: would upsert technician_profiles for {auth_user_id}.")
        return

    engine = create_engine(_database_url())
    with engine.begin() as connection:
        resident_exists = connection.scalar(
            text("SELECT true FROM residents WHERE id = :id"),
            {"id": auth_user_id},
        )
        if resident_exists:
            raise SystemExit("Refusing to provision Technician profile for an existing Resident UUID.")

        bql_exists = connection.scalar(
            text("SELECT true FROM bql_staff WHERE id = :id"),
            {"id": auth_user_id},
        )
        if bql_exists:
            raise SystemExit("Refusing to provision Technician profile for an existing BQL staff UUID.")

        connection.execute(
            text(
                """
                INSERT INTO technician_profiles (id, email, full_name, phone_number, is_active, is_available)
                VALUES (:id, :email, :full_name, :phone_number, true, true)
                ON CONFLICT (id) DO UPDATE
                SET email = EXCLUDED.email,
                    full_name = COALESCE(EXCLUDED.full_name, technician_profiles.full_name),
                    phone_number = COALESCE(EXCLUDED.phone_number, technician_profiles.phone_number),
                    is_active = true,
                    updated_at = now()
                """
            ),
            {
                "id": auth_user_id,
                "email": email,
                "full_name": full_name,
                "phone_number": phone_number,
            },
        )

    print(f"Provisioned Technician profile {auth_user_id}.")


def deactivate_technician(auth_user_id: UUID, dry_run: bool) -> None:
    """Deactivate a Technician profile after explicit operator confirmation."""
    if dry_run:
        print(f"DRY RUN: would deactivate technician_profiles {auth_user_id}.")
        return

    confirmation = input(
        f"Type {auth_user_id} to deactivate this Technician profile: "
    )
    if confirmation != str(auth_user_id):
        raise SystemExit("Confirmation did not match; aborting.")

    engine = create_engine(_database_url())
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                UPDATE technician_profiles
                SET is_active = false,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": auth_user_id},
        )
        if result.rowcount == 0:
            raise SystemExit("Technician profile was not found.")

    print(f"Deactivated Technician profile {auth_user_id}.")


def _validated_auth_user_payload(
    payload: Any,
    *,
    expected_id: UUID | None = None,
) -> SupabaseAuthUser:
    if not isinstance(payload, dict):
        raise SystemExit("Supabase Auth response was not a JSON object.")
    raw_id = payload.get("id")
    raw_email = payload.get("email")
    if not raw_id or not raw_email:
        raise SystemExit("Supabase Auth response is missing the user ID or email.")
    try:
        auth_user_id = UUID(str(raw_id))
    except ValueError as exc:
        raise SystemExit("Supabase Auth response contained an invalid user ID.") from exc
    if expected_id is not None and auth_user_id != expected_id:
        raise SystemExit("Supabase Auth response returned an unexpected user ID.")
    email = _normalize_email(str(raw_email))
    return SupabaseAuthUser(id=auth_user_id, email=email)


def _require_supabase_admin_settings() -> Settings:
    settings = get_settings()
    if not settings.supabase_url:
        raise SystemExit("SUPABASE_URL is required.")
    if not settings.supabase_secret_key:
        raise SystemExit("SUPABASE_SECRET_KEY is required.")
    return settings


def _database_url() -> str:
    database_url = get_settings().require_database_url()
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _normalize_email(value: str | None) -> str:
    if value is None:
        raise SystemExit("--email is required.")
    email = value.strip().casefold()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise SystemExit("A valid --email value is required.")
    return email



def _normalize_optional_phone(value: str | None) -> str | None:
    """Validate an optional E.164 Technician phone number."""
    cleaned = _clean_optional_text(value)
    if cleaned is None:
        return None
    if not cleaned.startswith("+") or not cleaned[1:].isdigit() or not 7 <= len(cleaned[1:]) <= 15:
        raise SystemExit("--phone-number must use E.164 format, for example +84901234567.")
    if cleaned[1] == "0":
        raise SystemExit("--phone-number must use E.164 format, for example +84901234567.")
    return cleaned


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None

def _parse_uuid(value: str | None) -> UUID:
    if not value:
        raise SystemExit("--auth-user-id is required.")
    try:
        return UUID(value)
    except ValueError as exc:
        raise SystemExit("--auth-user-id must be a valid UUID.") from exc


if __name__ == "__main__":
    raise SystemExit(main())
