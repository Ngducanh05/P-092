# Attachment Security

Current table: `ticket_attachments`.

Current fields include `file_url`, `file_type`, `mime_type`, `file_size`, and `ticket_id`.

## Decisions

- Treat `file_url` as CONFIDENTIAL. The name suggests a URL, but the safer target semantics are a private object path or stable object identifier.
- Do not rename `file_url` in this phase because existing code contracts are not fully defined.
- Do not store base64 file bodies, storage secret keys, service-role keys, or long-lived signed URLs.
- Store private object references in the database; generate short-lived signed URLs only through backend/storage infrastructure.
- Attachment access derives from parent ticket access:
  - resident: active membership to ticket unit,
  - technician: active assignment to ticket,
  - coordinator: approved management scope, pending clarification.

Storage bucket policies are deployment requirements and are not implemented here because no Supabase storage configuration exists in the repository.

