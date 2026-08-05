"""Backend-only private Supabase Storage bucket setup helper."""

from __future__ import annotations

import argparse
from typing import Any

import httpx

from src.config import get_settings


def parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(description="Create or verify the private FixIt attachment bucket.")
    arg_parser.add_argument("--dry-run", action="store_true", help="Show planned bucket changes without applying them.")
    return arg_parser


def main() -> int:
    args = parser().parse_args()
    settings = get_settings()
    if not settings.supabase_url:
        raise SystemExit("SUPABASE_URL is required.")
    if not settings.supabase_secret_key:
        raise SystemExit("SUPABASE_SECRET_KEY is required.")
    bucket_name = settings.supabase_storage_bucket
    headers = {
        "apikey": settings.supabase_secret_key,
        "Authorization": f"Bearer {settings.supabase_secret_key}",
        "Content-Type": "application/json",
    }
    base_url = f"{settings.supabase_url.rstrip('/')}/storage/v1"
    desired = {
        "public": False,
        "file_size_limit": settings.max_ticket_image_bytes,
        "allowed_mime_types": sorted(settings.parsed_allowed_ticket_image_mime_types),
    }

    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{base_url}/bucket/{bucket_name}", headers=headers)
        if response.status_code == 404:
            payload = {"id": bucket_name, "name": bucket_name, **desired}
            if args.dry_run:
                print(f"DRY RUN: would create private bucket {bucket_name}.")
                return 0
            create_response = client.post(f"{base_url}/bucket", headers=headers, json=payload)
            if create_response.status_code >= 400:
                raise SystemExit("Unable to create private storage bucket. Use the Dashboard manual steps in docs.")
            print(f"Created private bucket {bucket_name}.")
            return 0
        if response.status_code >= 400:
            raise SystemExit("Unable to inspect storage bucket. Use the Dashboard manual steps in docs.")
        current = _json(response)
        patch = _required_patch(current, desired)
        if not patch:
            print(f"Bucket {bucket_name} is already private and constrained.")
            return 0
        if args.dry_run:
            print(f"DRY RUN: would update private bucket {bucket_name} settings: {', '.join(sorted(patch))}.")
            return 0
        update_response = client.put(f"{base_url}/bucket/{bucket_name}", headers=headers, json=patch)
        if update_response.status_code >= 400:
            raise SystemExit("Unable to update storage bucket safely. Use the Dashboard manual steps in docs.")
    print(f"Updated private bucket {bucket_name} settings: {', '.join(sorted(patch))}.")
    return 0


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise SystemExit("Storage bucket response was not valid JSON.") from exc
    if not isinstance(data, dict):
        raise SystemExit("Storage bucket response was not a JSON object.")
    return data


def _required_patch(current: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    if current.get("public") is not False:
        patch["public"] = False
    if current.get("file_size_limit") != desired["file_size_limit"]:
        patch["file_size_limit"] = desired["file_size_limit"]
    current_mime_types = current.get("allowed_mime_types") or []
    if sorted(current_mime_types) != desired["allowed_mime_types"]:
        patch["allowed_mime_types"] = desired["allowed_mime_types"]
    return patch


if __name__ == "__main__":
    raise SystemExit(main())
