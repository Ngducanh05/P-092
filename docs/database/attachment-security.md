# Attachment Security

Ticket attachment objects are stored in a private Supabase Storage bucket. API responses return attachment metadata and signed download URLs only; raw Storage paths remain internal.

Authorization follows the parent ticket:

- Resident: active `resident_unit_memberships` row for the ticket unit.
- BQL: active `bql_staff` profile for current MVP system-wide read.

Upload sessions are backend-controlled and scoped by `resident_id`.
