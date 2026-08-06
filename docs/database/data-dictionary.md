# Data Dictionary

Final actor tables:

- `residents`: `id`, `phone_number`, `full_name`, `is_active`, timestamps. `id` maps to `auth.users.id`; phone is unique E.164.
- `bql_staff`: `id`, `email`, `full_name`, `is_active`, timestamps. `id` maps to `auth.users.id`; email is unique.
- `resident_unit_memberships`: Resident-to-unit membership with active/unlinked timestamps.

Ticket tables:

- `tickets.resident_id -> residents.id`
- `ticket_attachment_upload_sessions.resident_id -> residents.id`
- `ticket_status_history.changed_by_auth_user_id -> auth.users.id` in PostgreSQL migrations
- `notifications.recipient_auth_user_id -> auth.users.id` in PostgreSQL migrations
- `audit_logs.actor_auth_user_id -> auth.users.id` in PostgreSQL migrations

No final `public.users`, `role_enum`, Technician profile, Technician skill, or ticket assignment table exists.
