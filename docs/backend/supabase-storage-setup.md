# Supabase Storage Setup

Create a private bucket named `ticket-attachments` or set `SUPABASE_STORAGE_BUCKET` to another private bucket name. Do not make the bucket public.

Backend helper:

```powershell
python scripts/setup_supabase_storage.py --dry-run
python scripts/setup_supabase_storage.py
```

The helper requires `SUPABASE_URL` and `SUPABASE_SECRET_KEY`, never prints secret values, creates the bucket if missing, keeps it private, sets the maximum file size, and limits MIME types to:

- `image/jpeg`
- `image/png`
- `image/webp`

`SUPABASE_SECRET_KEY` supports current `sb_secret_*` keys and legacy service-role JWTs. Current `sb_secret_*` values are sent only as `apikey`; legacy service-role JWTs also keep `Authorization: Bearer <key>` compatibility.

If automated setup cannot inspect or update the bucket safely, configure it manually in the Supabase Dashboard:

1. Open Storage.
2. Create or select the configured bucket.
3. Set visibility to private.
4. Set the file size limit to `MAX_TICKET_IMAGE_BYTES`.
5. Set allowed MIME types to `image/jpeg`, `image/png`, and `image/webp`.
6. Do not add public read policies for this bucket.

Attachment flow:

1. The frontend asks FastAPI for a signed upload target with filename, MIME type, and size metadata.
2. FastAPI validates metadata, generates a server-owned private object path, requests a Supabase signed upload credential, creates a pending upload-session row, and returns `upload_id`.
3. Supabase signed upload targets expire after 7200 seconds.
4. The frontend uploads directly to Supabase Storage.
5. Ticket creation submits `attachment_upload_ids`; it never submits raw object paths.
6. FastAPI verifies each pending upload session and checks object metadata through the Supabase Storage object-info endpoint before creating attachment records.
7. Signed download URLs are generated only through `GET /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url` after backend authorization.

The database stores stable private object paths in trusted rows only. Normal ticket API responses do not expose private paths.

Live private bucket, signed upload, ticket attachment, and signed download validation remains BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED until `tests/integration` is run against a confirmed Supabase development/test project.
