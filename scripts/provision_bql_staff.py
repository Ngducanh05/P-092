"""Backend-only helper for BQL staff profile provisioning."""

from __future__ import annotations

import argparse
import getpass
import os
from uuid import UUID

import httpx
from sqlalchemy import create_engine, text

from src.config import get_settings
from src.database.session import get_database_url
from src.security.supabase_admin import build_supabase_admin_headers


def parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(description="Provision FixIt BQL staff profiles.")
    arg_parser.add_argument("action", choices=["provision", "sync", "deactivate"])
    arg_parser.add_argument("--email")
    arg_parser.add_argument("--auth-user-id")
    arg_parser.add_argument("--full-name")
    arg_parser.add_argument("--dry-run", action="store_true")
    return arg_parser


def require_secret() -> str:
    secret = get_settings().supabase_secret_key
    if not secret:
        raise SystemExit("SUPABASE_SECRET_KEY is required.")
    return secret


def create_auth_user(email: str, dry_run: bool) -> UUID:
    settings = get_settings()
    secret = require_secret()
    password = os.getenv("SUPABASE_USER_PASSWORD") or getpass.getpass("Temporary password: ")
    if dry_run:
        print("DRY RUN: would create Supabase Auth user by email.")
        return UUID("00000000-0000-0000-0000-000000000000")
    response = httpx.post(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
        headers=build_supabase_admin_headers(secret),
        json={"email": email, "password": password, "email_confirm": True},
        timeout=10.0,
    )
    response.raise_for_status()
    return UUID(response.json()["id"])


def upsert_bql_staff(auth_user_id: UUID, email: str, full_name: str | None, dry_run: bool) -> None:
    if dry_run:
        print(f"DRY RUN: would upsert bql_staff profile {auth_user_id}.")
        return
    engine = create_engine(get_database_url())
    with engine.begin() as connection:
        resident_exists = connection.scalar(text("SELECT true FROM residents WHERE id = :id"), {"id": auth_user_id})
        if resident_exists:
            raise SystemExit("Refusing to provision BQL profile for an existing Resident UUID.")
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
            {"id": auth_user_id, "email": email, "full_name": full_name},
        )
    print(f"Provisioned BQL staff profile {auth_user_id}.")


def deactivate_profile(auth_user_id: UUID, dry_run: bool) -> None:
    if dry_run:
        print(f"DRY RUN: would deactivate BQL staff profile {auth_user_id}.")
        return
    confirm = input(f"Type {auth_user_id} to deactivate this BQL staff profile: ")
    if confirm != str(auth_user_id):
        raise SystemExit("Confirmation did not match; aborting.")
    engine = create_engine(get_database_url())
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE bql_staff SET is_active = false, updated_at = now() WHERE id = :id"),
            {"id": auth_user_id},
        )
    print(f"Deactivated BQL staff profile {auth_user_id}.")


def main() -> None:
    args = parser().parse_args()
    if args.action == "deactivate":
        if not args.auth_user_id:
            raise SystemExit("--auth-user-id is required.")
        deactivate_profile(UUID(args.auth_user_id), args.dry_run)
        return

    if args.action == "provision":
        if not args.email:
            raise SystemExit("--email is required for provision.")
        auth_user_id = create_auth_user(args.email, args.dry_run)
        if args.dry_run:
            return
        upsert_bql_staff(auth_user_id, args.email, args.full_name, args.dry_run)
        return

    if not args.auth_user_id or not args.email:
        raise SystemExit("--auth-user-id and --email are required for sync.")
    upsert_bql_staff(UUID(args.auth_user_id), args.email, args.full_name, args.dry_run)


if __name__ == "__main__":
    main()
