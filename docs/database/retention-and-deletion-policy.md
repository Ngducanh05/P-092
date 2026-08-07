# Retention and Deletion Policy

Actor profile IDs map to Supabase Auth identities and may be referenced by historical records, so deactivation is preferred over deletion.

- Deactivate `residents.is_active`.
- Deactivate `bql_staff.is_active`.
- Deactivate `technician_profiles.is_active` and stop new assignment.
- End or preserve assignment history rather than deleting it.
- Unlink memberships with `is_active = false` and `unlinked_at`.
- Preserve Tickets, status history, audit logs, notifications, and attachment metadata unless an approved retention process applies.
