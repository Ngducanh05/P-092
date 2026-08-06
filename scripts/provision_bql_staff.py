"""Backend-only helper for trusted BQL staff profile provisioning."""

from __future__ import annotations

import argparse
import getpass
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import create_engine, text

from src.config import Settings, get_settings
from src.security.supabase_admin import build_supabase_admin_headers

DRY_RUN_UUID = UUID("00000000-0000-0000-0000-000000000000")


@dataclass(frozen=True)
class SupabaseAuthUser:
    """Minimum trusted Auth user fields required for BQL provisioning."""

    id: UUID
    email: str


def parser() -> argparse.ArgumentParser:
    """Build command-line arguments without exposing role selection."""
    arg_parser = argparse.ArgumentParser(
        description="Provision, sync, or deactivate FixIt BQL staff profiles."
    )
    arg_parser.add_argument("action", choices=["provision", "sync", "deactivate"])
    arg_parser.add_argument("--email")
    arg_parser.add_argument("--auth-user-id")
    arg_parser.add_argument("--full-name")
    arg_parser.add_argument("--dry-run", action="store_true")
    return arg_parser


def main() -> int:
    """Execute the requested trusted BQL profile administration action."""
    args = parser().parse_args()

    if args.action == "deactivate":
        if not args.auth_user_id:
            raise SystemExit("--auth-user-id is required for deactivate.")
        deactivate_profile(UUID(args.auth_user_id), dry_run=args.dry_run)
        return 0

    email = _normalize_email(args.email)

    if args.action == "provision":
        if args.dry_run:
            print(f"DRY RUN: would create Supabase Auth user for {email}.")
            print("DRY RUN: would upsert the matching bql_staff profile.")
            return 0

        auth_user = create_auth_user(email)
        upsert_bql_staff(
            auth_user_id=auth_user.id,
            email=auth_user.email,
            full_name=args.full_name,
            dry_run=False,
        )
        return 0

    if not args.auth_user_id:
        raise SystemExit("--auth-user-id is required for sync.")

    auth_user_id = UUID(args.auth_user_id)
    if args.dry_run:
        print(
            "DRY RUN: would validate the Supabase Auth user and upsert "
            f"bql_staff profile {auth_user_id}."
        )
        return 0

    auth_user = fetch_auth_user(auth_user_id)
    if auth_user.email != email:
        raise SystemExit(
            "Supabase Auth email does not match the requested BQL profile email."
        )

    upsert_bql_staff(
        auth_user_id=auth_user.id,
        email=auth_user.email,
        full_name=args.full_name,
        dry_run=False,
    )
    return 0


def create_auth_user(email: str) -> SupabaseAuthUser:
    """Create and return a Supabase email/password Auth identity."""
    settings = _require_supabase_admin_settings()
    password = os.getenv("SUPABASE_USER_PASSWORD") or getpass.getpass(
        "Temporary password: "
    )
    if not password:
        raise SystemExit("A non-empty temporary password is required.")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
                headers=build_supabase_admin_headers(settings.supabase_secret_key),
                json={
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                },
            )
    except httpx.RequestError as exc:
        raise SystemExit(
            "Unable to connect to Supabase Auth. Check SUPABASE_URL and the network."
        ) from exc

    if response.status_code >= 400:
        raise SystemExit(
            "Unable to create Supabase Auth user. "
            f"HTTP {response.status_code}."
        )

    return _validated_auth_user_payload(response.json(), expected_email=email)


def fetch_auth_user(auth_user_id: UUID) -> SupabaseAuthUser:
    """Read and validate an existing Supabase Auth identity before sync."""
    settings = _require_supabase_admin_settings()

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/"
                f"{auth_user_id}",
                headers=build_supabase_admin_headers(settings.supabase_secret_key),
            )
    except httpx.RequestError as exc:
        raise SystemExit(
            "Unable to connect to Supabase Auth. Check SUPABASE_URL and the network."
        ) from exc

    if response.status_code == 404:
        raise SystemExit("Supabase Auth user was not found.")
    if response.status_code >= 400:
        raise SystemExit(
            "Unable to inspect Supabase Auth user. "
            f"HTTP {response.status_code}."
        )

    auth_user = _validated_auth_user_payload(response.json())
    if auth_user.id != auth_user_id:
        raise SystemExit("Supabase Auth response returned an unexpected user ID.")
    return auth_user


def upsert_bql_staff(
    auth_user_id: UUID,
    email: str,
    full_name: str | None,
    dry_run: bool,
) -> None:
    """Create or reactivate the BQL profile using parameterized SQL."""
    if dry_run:
        print(f"DRY RUN: would upsert bql_staff profile {auth_user_id}.")
        return

    engine = create_engine(_database_url())
    with engine.begin() as connection:
        resident_exists = connection.scalar(
            text("SELECT true FROM residents WHERE id = :id"),
            {"id": auth_user_id},
        )
        if resident_exists:
            raise SystemExit(
                "Refusing to provision BQL profile for an existing Resident UUID."
            )

        connection.execute(
            text(
                """
                INSERT INTO bql_staff (id, email, full_name, is_active)
                VALUES (:id, :email, :full_name, true)
                ON CONFLICT (id) DO UPDATE
                SET email = EXCLUDED.email,
                    full_name = COALESCE(EXCLUDED.full_name, bql_staff.full_name),
                    is_active = true,
                    updated_at = now()
                """
            ),
            {
                "id": auth_user_id,
                "email": _normalize_email(email),
                "full_name": full_name,
            },
        )

    print(f"Provisioned BQL staff profile {auth_user_id}.")


def deactivate_profile(auth_user_id: UUID, dry_run: bool) -> None:
    """Deactivate a BQL profile after explicit operator confirmation."""
    if dry_run:
        print(f"DRY RUN: would deactivate BQL staff profile {auth_user_id}.")
        return

    confirmation = input(
        f"Type {auth_user_id} to deactivate this BQL staff profile: "
    )
    if confirmation != str(auth_user_id):
        raise SystemExit("Confirmation did not match; aborting.")

    engine = create_engine(_database_url())
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                UPDATE bql_staff
                SET is_active = false,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": auth_user_id},
        )
        if result.rowcount == 0:
            raise SystemExit("BQL staff profile was not found.")

    print(f"Deactivated BQL staff profile {auth_user_id}.")


def _validated_auth_user_payload(
    payload: Any,
    *,
    expected_email: str | None = None,
) -> SupabaseAuthUser:
    """Validate only the minimum Auth payload required by this script."""
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

    email = _normalize_email(str(raw_email))
    if expected_email is not None and email != _normalize_email(expected_email):
        raise SystemExit("Supabase Auth response email does not match the request.")

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


if __name__ == "__main__":
    raise SystemExit(main())
