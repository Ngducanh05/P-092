# Supabase Storage Setup

Create a private bucket named `ticket-attachments` or set `SUPABASE_STORAGE_BUCKET` to another private bucket name. Do not make the bucket public.

The frontend asks FastAPI for a signed upload URL with filename, MIME type, and size metadata. FastAPI validates the metadata, generates a path like `tickets/{auth_user_id}/{yyyy}/{mm}/{random_uuid}.{extension}`, and returns a short-lived upload target. The frontend uploads directly to Supabase Storage.

Allowed default image types are `image/jpeg`, `image/png`, and `image/webp`. SVG, HTML, executable content, unknown MIME types, empty metadata, traversal paths, and files larger than `MAX_TICKET_IMAGE_BYTES` are rejected.

The database stores only the stable private storage path in `ticket_attachments.file_url`. Signed download URLs are generated only after backend ticket authorization and are never stored.
