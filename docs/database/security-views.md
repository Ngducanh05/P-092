# Security Views

The migration creates two projections justified by confirmed resident and technician workflows:

## `resident_ticket_view`

- View owner: migration/database owner.
- Security behavior: `WITH (security_invoker = true)` so underlying RLS remains effective on supported PostgreSQL versions.
- Underlying RLS dependency: `tickets`.
- Exposed columns: ticket id, title, description, category, priority, status, location description, created/updated/resolved timestamps.
- Excluded columns: scoring breakdown, scoring reasons, AI confidence, model metadata, audit logs, user auth/contact fields, service metadata.

## `technician_ticket_view`

- View owner: migration/database owner.
- Security behavior: `WITH (security_invoker = true)`.
- Underlying RLS dependency: `tickets` and `ticket_assignments`.
- Exposed columns: ticket id, title, description, category, priority, status, location description, assignment timestamps.
- Excluded columns: severity score, red flag score, impact score, density score, age score, total score, scoring reasons, AI confidence, raw AI analysis metadata, audit metadata, resident authentication data.

## Coordinator View

Status: REQUIRES BUSINESS CLARIFICATION.

No coordinator view is created because coordinator management scope is not defined.

