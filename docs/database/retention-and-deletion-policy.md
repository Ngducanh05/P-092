# Retention and Deletion Policy

Resident and BQL profile deletion is restricted because profile IDs map to Supabase Auth identities and historical operational records.

Preferred lifecycle actions:

- Deactivate `residents.is_active`.
- Deactivate `bql_staff.is_active`.
- Unlink memberships with `resident_unit_memberships.is_active = false` and `unlinked_at`.
- Preserve tickets, status history, audit logs, and attachment metadata unless a separate approved data-retention process applies.
