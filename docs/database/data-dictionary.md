# Data Dictionary

## Actor tables

- `residents`: Auth-linked Resident profile with unique E.164 phone.
- `bql_staff`: Auth-linked BQL profile with unique email.
- `technician_profiles`: Auth-linked Technician profile with email, optional contact fields, `is_active`, and `is_available`.
- `technician_skills`: unique `(technician_id, category)` qualifications.

The application has no `public.users` table and no `role_enum`.

## Assignment tables

- `ticket_assignments.ticket_id -> tickets.id`
- `ticket_assignments.technician_id -> technician_profiles.id`
- `ticket_assignments.assigned_by_auth_user_id -> auth.users.id` in PostgreSQL
- `status`: `assigned`, `accepted`, `in_progress`, `completed`, `unable_to_handle`
- `assignment_note`: optional BQL routing note
- `work_note`: Technician cause/material/action note
- `unable_reason`: required when status is `unable_to_handle`
- a partial unique index enforces one active assignment per Ticket

## Shared identity references

- `ticket_status_history.changed_by_auth_user_id -> auth.users.id`
- `notifications.recipient_auth_user_id -> auth.users.id`
- `audit_logs.actor_auth_user_id -> auth.users.id`
